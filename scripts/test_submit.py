"""Offline behavioral checks. Never contact external SMTP."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from email.parser import BytesParser
from email import policy
import smtplib
import zipfile

spec=importlib.util.spec_from_file_location('submit', Path(__file__).with_name('submit.py'))
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class FakeSMTP:
    def __init__(self, error=False): self.calls=0; self.error=error
    def sendmail(self, sender, to, raw):
        self.calls+=1
        if self.error: raise smtplib.SMTPServerDisconnected('test-only')
        return {}
    def quit(self): pass
    def close(self): pass

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.patch=patch.object(s,'CONFIG_DIR',self.root/'config'); self.patch.start()
        self.config=self.root/'config/smtp.json'
        s.private_write(self.root/'config/smtp.secret','offline-test-secret')
        s.dump(self.config,dict(host='smtp.example.org',port=465,security='ssl',username='author@example.org',from_email='author@example.org',from_name='作者',password_file=str(self.root/'config/smtp.secret')))
        (self.root/'body.txt').write_text('编辑您好：这是中文稿件。',encoding='utf8')
        (self.root/'article.md').write_text('# 中文标题\n\n证据与方法。',encoding='utf8')
        with zipfile.ZipFile(self.root/'review.docx', 'w') as z:
            z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
            z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Offline review fixture</w:t></w:r></w:p></w:body></w:document>')
        self.job=dict(outlet='jiqizhixin',to='editor@example.org',mode='submission',recipient_basis='user_confirmed',recipient_evidence='User selected this test-only address',subject='【投稿】中文研究',body_file='body.txt',attachments=['article.md','review.docx'],blockers=[])
    def tearDown(self): self.patch.stop(); self.temp.cleanup()
    def package(self,name='package'):
        s.dump(self.root/'job.json',self.job)
        s.prepare(SimpleNamespace(job=str(self.root/'job.json'),out=str(self.root/name),config=str(self.config)))
        if not self.job['blockers']:
            s.record_approval(SimpleNamespace(package=str(self.root/name),statement='OFFLINE TEST fixture only: human reviewed this version and confirmed sending'))
        return self.root/name
    def args(self,p,execute=True): return SimpleNamespace(package=str(p),execute=execute,config=str(self.config))
    def test_unicode_snapshot_and_dry_run(self):
        p=self.package(); raw=(p/'draft.eml').read_bytes()
        msg=BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(str(msg['Subject']),self.job['subject'])
        self.assertEqual(next(msg.iter_attachments()).get_filename(),'article.md')
        (self.root/'article.md').write_text('changed')
        self.assertIn('证据与方法',next(msg.iter_attachments()).get_payload(decode=True).decode())
        with patch.object(s,'connect') as c:
            s.send(self.args(p,False)); c.assert_not_called()
    def test_tampered_mail_is_rejected(self):
        p=self.package(); (p/'draft.eml').write_bytes(b'changed')
        with self.assertRaises(ValueError): s.send(self.args(p))
    def test_explicit_send_without_human_approval_is_blocked(self):
        p=self.package(); (p/'human-approval.json').unlink()
        with patch.object(s,'connect') as client:
            with self.assertRaises(ValueError): s.send(self.args(p))
            client.assert_not_called()
    def test_edited_review_word_blocks_approval_and_send(self):
        p=self.package()
        (p/'attachments/review.docx').write_bytes(b'human edited this file')
        with patch.object(s,'connect') as client:
            with self.assertRaisesRegex(ValueError, 'attachment changed'):
                s.record_approval(SimpleNamespace(package=str(p),statement='test confirmation'))
            with self.assertRaisesRegex(ValueError, 'attachment changed'):
                s.send(self.args(p))
            client.assert_not_called()
    def test_changed_review_body_and_manifest_are_rejected(self):
        p=self.package()
        original=(p/'body.txt').read_bytes()
        (p/'body.txt').write_text('Changed recipient-facing email')
        with self.assertRaisesRegex(ValueError, 'email body changed'): s.check_package(p)
        (p/'body.txt').write_bytes(original)
        review=s.read_json(p/'review.json'); review['attachments']=[]
        s.dump(p/'review.json', review)
        with self.assertRaisesRegex(ValueError, 'manifest'): s.check_package(p)
    def test_missing_or_fake_word_blocks_submission(self):
        (self.root/'review.docx').write_bytes(b'not a Word file')
        with self.assertRaisesRegex(ValueError, 'Invalid Word'): self.package()
        self.job['attachments']=['article.md']
        s.dump(self.root/'job.json',self.job)
        p=self.root/'missing-word'
        s.prepare(SimpleNamespace(job=str(self.root/'job.json'),out=str(p),config=str(self.config)))
        with patch.object(s,'connect') as client:
            with self.assertRaises(ValueError):
                s.record_approval(SimpleNamespace(package=str(p),statement='test confirmation'))
            with self.assertRaises(ValueError): s.send(self.args(p))
            client.assert_not_called()
    def test_old_approval_cannot_authorize_new_word(self):
        p=self.package()
        with zipfile.ZipFile(self.root/'review.docx', 'a') as z: z.writestr('docProps/new-version.xml','<version>2</version>')
        q=self.package('new-word')
        (q/'human-approval.json').write_bytes((p/'human-approval.json').read_bytes())
        with patch.object(s,'connect') as client:
            with self.assertRaisesRegex(ValueError, 'does not match'): s.send(self.args(q))
            client.assert_not_called()
    def test_blockers_and_secret_attachment(self):
        self.job['blockers']=['Missing selected outlet']; p=self.package()
        with self.assertRaises(ValueError): s.send(self.args(p))
        self.job['attachments']=['config/smtp.secret']
        with self.assertRaises(ValueError): self.package('secret-package')
    def test_channel_validation(self):
        self.job.update(outlet='aiera',to='daijia@aiera.com.cn',recipient_basis='registry')
        with self.assertRaises(ValueError): s.validate_job(self.job)
        self.job['mode']='inquiry'; s.validate_job(self.job)
        self.job['to']='ok@example.org\r\nBcc: other@example.org'
        with self.assertRaises(ValueError): s.validate_job(self.job)
    def test_success_and_duplicate_after_reprepare(self):
        p=self.package(); fake=FakeSMTP()
        with patch.object(s,'connect',return_value=fake): s.send(self.args(p))
        self.assertEqual(json.loads((p/'receipt.json').read_text())['status'],'accepted_by_smtp')
        q=self.package('package2')
        with patch.object(s,'connect',return_value=fake):
            with self.assertRaises(ValueError): s.send(self.args(q))
        self.assertEqual(fake.calls,1)
    def test_ambiguous_data_never_retried(self):
        p=self.package(); fake=FakeSMTP(error=True)
        with patch.object(s,'connect',return_value=fake):
            with self.assertRaises(smtplib.SMTPServerDisconnected): s.send(self.args(p))
            with self.assertRaises(ValueError): s.send(self.args(p))
        self.assertEqual(fake.calls,1)
        self.assertIn('delivery_uncertain_do_not_retry', next((self.root/'config/sent').glob('*.json')).read_text())
    def test_auth_failure_can_retry(self):
        p=self.package()
        with patch.object(s,'connect',side_effect=smtplib.SMTPAuthenticationError(535,b'test')):
            with self.assertRaises(smtplib.SMTPAuthenticationError): s.send(self.args(p))
        fake=FakeSMTP()
        with patch.object(s,'connect',return_value=fake): s.send(self.args(p))
        self.assertEqual(fake.calls,1)
    def test_renderer(self):
        text=s.render_markdown('# 标题\n\n<script>alert(1)</script>\n\n| A | B |\n| --- | --- |\n| **1** | 2 |')
        self.assertIn('&lt;script&gt;',text); self.assertIn('<table>',text)
        self.assertIn('<strong>1</strong>',text)
        with self.assertRaises(ValueError): s.render_markdown('[bad](javascript:evil)')

if __name__=='__main__':
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()): unittest.main(verbosity=2)
