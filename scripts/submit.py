#!/usr/bin/env python3
"""Local, dependency-free paper outreach helpers. No LLM calls; send is opt-in."""
import argparse
import base64
import datetime as dt
import email.policy
import email.utils
from email.message import EmailMessage
from email.parser import BytesParser
import getpass
import hashlib
import html
from html.parser import HTMLParser
import json
import mimetypes
import os
from pathlib import Path
import re
import smtplib
import ssl
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path.home() / '.config' / 'paper-wechat-submit'
DEFAULT_CONFIG = CONFIG_DIR / 'smtp.json'
MAX_BYTES = 20 * 1024 * 1024

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def fail(message):
    raise ValueError(message)

def private_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        fail('Refusing a symbolic-link output: ' + str(path))
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data if isinstance(data, bytes) else data.encode('utf-8'))

def dump(path, obj):
    private_write(path, json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def address(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', value):
        fail('Expected one bare ASCII email address (no display name/CC/list).')
    return value

def single_line(value):
    if not isinstance(value, str) or not value.strip() or '\r' in value or '\n' in value:
        fail('Invalid or empty mail header.')
    return value

def outlets():
    return read_json(ROOT / 'references' / 'outlets.json')

def config_template():
    return dict(host='', port=465, security='ssl', username='', from_email='',
                from_name='', password_file=str(CONFIG_DIR / 'smtp.secret'))

def load_config(path, auth=False):
    path = Path(path).expanduser().resolve()
    c = read_json(path)
    for k in ('host', 'username', 'from_email'):
        single_line(c.get(k, ''))
    address(c['from_email'])
    if c.get('security') not in ('ssl', 'starttls'):
        fail('Only ssl or starttls is supported; plaintext SMTP is disabled.')
    if not isinstance(c.get('port'), int) or not 1 <= c['port'] <= 65535:
        fail('Invalid SMTP port.')
    if c.get('from_name'):
        single_line(c['from_name'])
    if auth:
        if c.get('password_env'):
            password = os.environ.get(c['password_env'], '')
        else:
            p = Path(c.get('password_file', '')).expanduser()
            if not p.is_absolute():
                p = path.parent / p
            if not p.is_file() or p.is_symlink() or p.stat().st_mode & 0o077:
                fail('Credential file must be a regular owner-only file (chmod 600).')
            password = p.read_text(encoding='utf-8').rstrip('\r\n')
        if not password:
            fail('Missing SMTP credential.')
        return c, password
    return c

def connect(c, password):
    context = ssl.create_default_context()
    client = None
    try:
        if c['security'] == 'ssl':
            client = smtplib.SMTP_SSL(c['host'], c['port'], timeout=25, context=context)
        else:
            client = smtplib.SMTP(c['host'], c['port'], timeout=25)
            client.ehlo()
            client.starttls(context=context)
        client.ehlo()
        client.login(c['username'], password)
        return client
    except Exception:
        if client is not None:
            client.close()
        raise

def configure(args):
    p = Path(args.config).expanduser()
    c = read_json(p) if p.exists() else config_template()
    for key, label in [('from_email', '发件邮箱'), ('from_name', '署名（可暂空）'),
                       ('host', 'SMTP 服务器'), ('security', '加密 ssl/starttls'),
                       ('port', '端口'), ('username', '登录用户名')]:
        default = c.get(key, '') or (c.get('from_email', '') if key == 'username' else '')
        val = input(f'{label} [{default}]: ').strip()
        c[key] = int(val or default) if key == 'port' else (val or default)
    secret = getpass.getpass('SMTP 授权码（隐藏输入，留空保留已有凭据）: ')
    if secret:
        secret_path = p.parent / 'smtp.secret'
        private_write(secret_path, secret)
        c['password_file'] = str(secret_path.resolve())
        c.pop('password_env', None)
    dump(p, c)
    load_config(p, auth=True)
    print('配置已保存；运行 smtp-check 检查 TLS 和认证。')

class Page(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.parts, self.links, self.images, self.meta = base, [], [], [], []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if tag == 'a' and a.get('href'):
            self.links.append(urllib.parse.urljoin(self.base, a['href']))
        if tag == 'img' and a.get('src'):
            self.images.append({'url': urllib.parse.urljoin(self.base, a['src']), 'alt': a.get('alt', '')})
        if tag == 'meta' and a.get('content'):
            self.meta.append(a)
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'li', 'tr', 'br'):
            self.parts.append('\n')
        if tag in ('td', 'th'):
            self.parts.append(' | ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def collect(args):
    url = args.url
    if urllib.parse.urlparse(url).scheme not in ('https', 'http'):
        fail('Use an HTTP(S) source URL.')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    req = urllib.request.Request(url, headers={'User-Agent': 'PaperWechatSubmit/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            fail('Source larger than 20 MB; retrieve intentionally with another tool.')
        final_url = r.geturl()
        ctype = r.headers.get_content_type()
        charset = r.headers.get_content_charset() or 'utf-8'
    meta = dict(requested_url=url, final_url=final_url, retrieved_at=now(), content_type=ctype, sha256=digest(data))
    if data.startswith(b'%PDF'):
        private_write(out / 'source.pdf', data)
        meta['status'] = 'downloaded_pdf_requires_reading'
    else:
        content = data.decode(charset, errors='replace')
        private_write(out / 'source.html', content)
        page = Page(final_url)
        page.feed(content)
        private_write(out / 'source.txt', re.sub(r'\n\s*\n+', '\n\n', ''.join(page.parts)))
        meta.update(links=list(dict.fromkeys(page.links)), images=page.images, metadata=page.meta,
                    status='extracted_html_review_required')
    dump(out / 'source.json', meta)
    print(str(out.resolve()))

def safe_url(url):
    parsed = urllib.parse.urlsplit(html.unescape(url))
    if parsed.scheme and parsed.scheme not in ('http', 'https', 'mailto'):
        fail('Unsafe URL scheme in Markdown.')
    if url.startswith('//') or '\\' in url:
        fail('Unsupported Markdown URL.')
    return url

def inline(value):
    escaped = html.escape(value, quote=True)
    escaped = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', lambda m: '<a href="' + safe_url(m[2]) + '">' + m[1] + '</a>', escaped)
    escaped = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
    return escaped

def render_markdown(content):
    lines = content.splitlines()
    parts, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        h = re.match(r'^(#{1,6}) (.+)$', line)
        img = re.fullmatch(r'!\[([^\]]*)\]\(([^\s)]+)\)', line)
        if h:
            n = len(h[1])
            parts.append(f'<h{n}>{inline(h[2])}</h{n}>')
        elif img:
            src = html.escape(safe_url(img[2]), quote=True)
            parts.append(f'<figure><img src="{src}" alt="{html.escape(img[1], quote=True)}"><figcaption>{inline(img[1])}</figcaption></figure>')
        elif line.startswith('|') and i + 1 < len(lines) and re.fullmatch(r'[\s|:\-]+', lines[i+1]):
            cells = [x.strip() for x in line.strip('|').split('|')]
            table = '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + inline(c) + '</th>' for c in cells) + '</tr></thead><tbody>'
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                table += '<tr>' + ''.join('<td>' + inline(c.strip()) + '</td>' for c in lines[i].strip().strip('|').split('|')) + '</tr>'
                i += 1
            parts.append(table + '</tbody></table></div>')
            continue
        elif line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].strip().startswith('- '):
                items.append('<li>' + inline(lines[i].strip()[2:]) + '</li>')
                i += 1
            parts.append('<ul>' + ''.join(items) + '</ul>')
            continue
        elif line.startswith('> '):
            parts.append('<blockquote>' + inline(line[2:]) + '</blockquote>')
        else:
            para = [line]
            while i + 1 < len(lines) and lines[i+1].strip() and not re.match(r'^(#|\||- |!\[|> )', lines[i+1].strip()):
                i += 1
                para.append(lines[i].strip())
            parts.append('<p>' + inline(' '.join(para)) + '</p>')
        i += 1
    title = next((x[2:] for x in lines if x.startswith('# ')), '论文推文')
    css = 'body{margin:0;background:#f3f5f7;color:#202b38;font:17px/1.9 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}article{max-width:780px;margin:36px auto;padding:48px;background:#fff}h1{font-size:30px;line-height:1.45}h2{font-size:23px;margin-top:40px;border-left:4px solid #19757b;padding-left:14px}h3{font-size:19px}a{color:#126e86;overflow-wrap:anywhere}img{width:100%;height:auto}figure{margin:30px 0}figcaption{font-size:13px;color:#66717e}table{border-collapse:collapse;min-width:480px;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #dde4e8;text-align:left}th{background:#edf5f5}.table-wrap{overflow-x:auto}blockquote{border-left:3px solid #8ab5b8;padding-left:18px;color:#50606b}code{background:#eef2f4;padding:2px 5px}@media(max-width:700px){article{margin:0;padding:24px}h1{font-size:25px}body{font-size:16px}}'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><style>' + css + '</style></head><body><article>' + '\n'.join(parts) + '</article></body></html>'

def resolve_input(base, value):
    p = Path(value).expanduser()
    return (p if p.is_absolute() else base / p).resolve()

def validate_job(j):
    outlet = next((x for x in outlets() if x['id'] == j['outlet']), None)
    if not outlet:
        fail('Unknown outlet id.')
    address(j['to'])
    mode = j.get('mode', 'submission')
    if mode not in ('submission', 'inquiry'):
        fail('Mode must be submission or inquiry.')
    basis = j.get('recipient_basis', '')
    if basis == 'registry':
        if j['to'] not in outlet['emails']:
            fail('Recipient is not in this outlet registry.')
        if mode == 'submission' and outlet['kind'] != 'submission':
            fail('This is not a verified submission channel; use inquiry or a user-confirmed address.')
        if mode == 'submission' and outlet['evidence'] != 'official':
            fail('Submission address needs current verification or user confirmation.')
        checked = dt.date.fromisoformat(outlet['checked_on'])
        if (dt.date.today() - checked).days > 30:
            fail('Contact check is older than 30 days; reverify and record evidence in job.')
    elif basis not in ('user_confirmed', 'official_rechecked') or not j.get('recipient_evidence', '').strip():
        fail('Record recipient_basis and recipient_evidence for a confirmed custom/current address.')
    single_line(j['subject'])
    if j['outlet'] == 'qbitai' and '投稿' not in j['subject'] and '爆料' not in j['subject'] and mode == 'submission':
        fail('量子位主题须包含“投稿”或“爆料”。')
    return outlet

def prepare(args):
    job_path = Path(args.job).resolve()
    j = read_json(job_path)
    outlet = validate_job(j)
    out = Path(args.out).resolve()
    if out.exists():
        fail('Package output already exists; use a new folder to preserve the reviewed version.')
    attachments = []
    config_path = Path(args.config).expanduser()
    c = load_config(config_path) if config_path.exists() and read_json(config_path).get('from_email') else None
    forbidden = {config_path.resolve()}
    if c and c.get('password_file'):
        forbidden.add(resolve_input(config_path.resolve().parent, c['password_file']))
    body_path = resolve_input(job_path.parent, j['body_file'])
    def public_file(path):
        if path in forbidden or CONFIG_DIR.resolve() in path.parents or path.name.endswith(('.secret', '.env')):
            fail('Configuration or credential files cannot enter a mail package.')
        if not path.is_file():
            fail('Missing input: ' + str(path))
        return path.read_bytes()
    body = public_file(body_path).decode('utf-8')
    if not body.strip():
        fail('Email body is empty.')
    size = len(body.encode('utf-8'))
    for item in j.get('attachments', []):
        p = resolve_input(job_path.parent, item)
        data = public_file(p)
        if p.name in [x[0] for x in attachments]:
            fail('Attachment filenames must be unique.')
        size += len(data)
        attachments.append((p.name, data))
    if size > 15 * 1024 * 1024:
        fail('Attachments exceed 15 MB raw; compress or use approved links.')
    blockers = list(j.get('blockers', []))
    if j.get('mode', 'submission') == 'submission' and not any(n.lower().endswith('.docx') for n,d in attachments):
        blockers.append('Word manuscript must be generated and attached for human review')
    if not c:
        blockers.append('SMTP sender is not configured')
    sender = c['from_email'] if c else 'draft@example.invalid'
    msg = EmailMessage(policy=email.policy.SMTP)
    msg['From'] = email.utils.formataddr((c.get('from_name', ''), sender)) if c else sender
    msg['To'], msg['Subject'] = j['to'], j['subject']
    msg['Date'], msg['Message-ID'] = email.utils.formatdate(localtime=True), email.utils.make_msgid(domain=sender.split('@')[-1])
    msg.set_content(body)
    for name, data in attachments:
        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        main, sub = mime.split('/', 1)
        msg.add_attachment(data, maintype=main, subtype=sub, filename=name)
    raw = msg.as_bytes()
    content_key = digest(json.dumps([sender, j['to'], j['subject'], body, [(n, digest(d)) for n,d in attachments]], ensure_ascii=False).encode())
    out.mkdir(parents=True, mode=0o700)
    (out / 'attachments').mkdir(mode=0o700)
    for name, data in attachments:
        private_write(out / 'attachments' / name, data)
    private_write(out / 'body.txt', body)
    private_write(out / 'draft.eml', raw)
    review = dict(outlet=outlet['name'], to=j['to'], sender=sender, subject=j['subject'],
                  mode=j.get('mode', 'submission'), message_id=str(msg['Message-ID']), created_at=now(),
                  eml_sha256=digest(raw), content_key=content_key, recipient_basis=j['recipient_basis'],
                  recipient_evidence=j.get('recipient_evidence', outlet['sources']), blockers=blockers,
                  attachments=[dict(name=n, bytes=len(d), sha256=digest(d)) for n,d in attachments])
    dump(out / 'review.json', review)
    print(json.dumps(review, ensure_ascii=False, indent=2))

def check_package(path):
    p = Path(path).resolve()
    r = read_json(p / 'review.json')
    raw = (p / 'draft.eml').read_bytes()
    if digest(raw) != r['eml_sha256']:
        fail('Mail changed after prepare; prepare a new package.')
    msg = BytesParser(policy=email.policy.default).parsebytes(raw)
    if str(msg['To']) != r['to'] or email.utils.parseaddr(msg['From'])[1] != r['sender'] or str(msg['Subject']) != r['subject']:
        fail('Mail headers do not match review.')
    address(r['to'])
    return p, r, raw

def record_approval(args):
    p, r, raw = check_package(args.package)
    if r['blockers']:
        fail('Resolve manuscript/recipient blockers before recording human approval.')
    if not args.statement.strip():
        fail('Record the actual user confirmation after human review of this Word version.')
    approval = dict(approved_at=now(), statement=args.statement, eml_sha256=r['eml_sha256'],
                    to=r['to'], subject=r['subject'], attachments=r['attachments'])
    dump(p / 'human-approval.json', approval)
    print('Human confirmation recorded for this exact mail snapshot. No email sent.')

def send(args):
    p, r, raw = check_package(args.package)
    if not args.execute:
        print(json.dumps(dict(dry_run=True, **r), ensure_ascii=False, indent=2))
        return
    if r['blockers']:
        fail('Unresolved blockers: ' + '; '.join(r['blockers']))
    approval_path = p / 'human-approval.json'
    if not approval_path.is_file():
        fail('Human review and explicit confirmation are required; no human-approval.json exists.')
    approval = read_json(approval_path)
    if approval.get('eml_sha256') != r['eml_sha256'] or approval.get('to') != r['to'] or not approval.get('statement'):
        fail('Human confirmation does not match this mail snapshot; review and confirm the new version.')
    c, password = load_config(args.config, auth=True)
    if c['from_email'] != r['sender']:
        fail('SMTP sender differs from the reviewed sender; prepare again.')
    logs = CONFIG_DIR / 'sent'
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    log = logs / (r['content_key'] + '.json')
    # Exclusive persistent claim prevents concurrent or repeated DATA for the same content.
    try:
        fd = os.open(str(log), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        previous = read_json(log)
        fail('Duplicate/in-flight submission blocked. Check local receipt and Message-ID: ' + previous.get('message_id', 'unknown'))
    with os.fdopen(fd, 'w') as f:
        json.dump(dict(status='connecting', message_id=r['message_id'], to=r['to'], at=now()), f)
    client = None
    stage = 'connecting'
    try:
        client = connect(c, password)
        stage = 'data_may_have_been_sent'
        dump(log, dict(status=stage, message_id=r['message_id'], to=r['to'], at=now()))
        refused = client.sendmail(r['sender'], [r['to']], raw)
        if refused:
            fail('SMTP refused recipient.')
        receipt = dict(status='accepted_by_smtp', message_id=r['message_id'], to=r['to'], at=now(), eml_sha256=r['eml_sha256'])
        dump(log, receipt)
        dump(p / 'receipt.json', receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    except Exception as exc:
        if stage == 'connecting':
            log.unlink(missing_ok=True)
        else:
            dump(log, dict(status='delivery_uncertain_do_not_retry', message_id=r['message_id'], to=r['to'], at=now(), error_type=type(exc).__name__))
        raise
    finally:
        if client:
            # QUIT errors after accepted DATA must not convert success to failure.
            try:
                client.quit()
            except Exception:
                client.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(DEFAULT_CONFIG))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('outlets')
    commands.add_parser('init-config')
    commands.add_parser('configure')
    commands.add_parser('smtp-check')
    c = commands.add_parser('collect'); c.add_argument('url'); c.add_argument('--out', required=True)
    r = commands.add_parser('render'); r.add_argument('markdown'); r.add_argument('--out', required=True); r.add_argument('--embed-images', action='store_true')
    p = commands.add_parser('prepare'); p.add_argument('job'); p.add_argument('--out', required=True)
    s = commands.add_parser('send'); s.add_argument('package'); s.add_argument('--execute', action='store_true')
    a = commands.add_parser('record-approval'); a.add_argument('package'); a.add_argument('--statement', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'outlets':
            for o in outlets():
                print(f"{o['id']:14} {o['name']:10} {o['kind']:12} {', '.join(o['emails']) or '无可靠邮箱'} | {o['note']}")
        elif args.command == 'init-config':
            path = Path(args.config).expanduser()
            if path.exists():
                print('已有配置，保留原文件：' + str(path))
            else:
                dump(path, config_template()); print(str(path))
        elif args.command == 'configure':
            configure(args)
        elif args.command == 'smtp-check':
            c, secret = load_config(args.config, auth=True)
            client = connect(c, secret)
            try:
                print(json.dumps(dict(status='tls_and_login_ok', host=c['host'], port=c['port'], sender=c['from_email'], tls=client.sock.version(), checked_at=now(), mail_sent=False), ensure_ascii=False))
            finally:
                try:
                    client.quit()
                except Exception:
                    client.close()
        elif args.command == 'collect':
            collect(args)
        elif args.command == 'render':
            content = Path(args.markdown).read_text(encoding='utf-8')
            rendered = render_markdown(content)
            if args.embed_images:
                base = Path(args.markdown).resolve().parent
                def embed(match):
                    src = html.unescape(match[1])
                    if urllib.parse.urlsplit(src).scheme:
                        return match[0]
                    image_path = (base / src).resolve()
                    if base not in image_path.parents:
                        fail('Embedded images must be inside the article directory.')
                    mime = mimetypes.guess_type(image_path.name)[0]
                    if mime not in ('image/png', 'image/jpeg', 'image/gif', 'image/webp'):
                        fail('Embedded images must use a supported raster format.')
                    data = image_path.read_bytes()
                    if len(data) > 10 * 1024 * 1024:
                        fail('Image too large to embed.')
                    return 'src="data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii') + '"'
                rendered = re.sub(r'src="([^"]+)"', embed, rendered)
            private_write(args.out, rendered); print(str(Path(args.out).resolve()))
        elif args.command == 'prepare':
            prepare(args)
        elif args.command == 'send':
            send(args)
        elif args.command == 'record-approval':
            record_approval(args)
    except (ValueError, KeyError, OSError, smtplib.SMTPException) as exc:
        # Never dump raw SMTP responses, config, authentication bytes or tracebacks.
        message = str(exc) if isinstance(exc, (ValueError, KeyError)) else type(exc).__name__
        print('ERROR: ' + message, file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
