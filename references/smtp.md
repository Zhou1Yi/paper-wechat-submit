# SMTP 命令与投稿任务格式

在技能目录运行下列命令；任意目录可使用脚本绝对路径。先写稿、预览，后发送。

```sh
python3 scripts/submit.py outlets
python3 scripts/submit.py init-config
python3 scripts/submit.py configure
python3 scripts/submit.py smtp-check
python3 scripts/submit.py collect https://example.org/paper --out /absolute/path/sources
python3 scripts/submit.py render /absolute/path/article.md --out /absolute/path/article.html --embed-images
python3 scripts/submit.py prepare /absolute/path/job.json --out /absolute/path/package-v1
python3 scripts/submit.py send /absolute/path/package-v1
# 人工审核 Word 后、用户明确确认当前版本及收件人时才记录：
python3 scripts/submit.py record-approval /absolute/path/package-v1 --statement '记录用户审核后对本版本明确确认发送的原意'
# 有当前版本人工确认记录后才可投递：
python3 scripts/submit.py send /absolute/path/package-v1 --execute
```

`--config /absolute/path/smtp.json` 是全局参数，放在子命令前。默认配置为 `~/.config/paper-wechat-submit/smtp.json`，`smtp.secret` 为独立凭据，权限 0600。这是本机文件存储，不是加密保险库，不将其复制进分享包。也可以配置 `password_env` 为已有环境变量名来替代 `password_file`；不要把密码作为命令行参数传入。

QQ 邮箱配置：`smtp.qq.com`、465、`ssl`、完整邮箱作为用户名、SMTP 授权码。[腾讯云官方连接器手册](https://main.qcloudimg.com/raw/document/product/pdf/1270_46586_cn.pdf) 列出了 QQ SMTP 服务器和 465/587 端口。其他服务商使用其官方参数；服务器必须支持本工具的用户名/授权码认证。无明文 SMTP、无关闭证书验证选项。

## job.json

路径相对 job.json 所在目录。下列仅为模式示意，实际任务写真实信息。

```json
{
  "outlet": "jiqizhixin",
  "mode": "submission",
  "to": "z@jqzx.ai",
  "recipient_basis": "registry",
  "subject": "【投稿】研究名称：有证据支持的一句话贡献",
  "body_file": "email.txt",
  "attachments": ["article.docx", "article.md", "article.html", "figures/overview.png"],
  "blockers": []
}
```

- `mode`: `submission` 全文投稿或 `inquiry` 咨询。新智元、极市、VALSE 的默认邮箱只能用于咨询。CVer 无默认邮箱，生成手动联系材料；不要猜邮箱。
- `recipient_basis`: `registry` 使用库中最近 30 天核验的官方地址；`official_rechecked` 用当次核实的官方地址，并写 `recipient_evidence`（具体 URL、核验日期及“投稿邮箱”证据）；`user_confirmed` 记录用户明确确认的地址及用途，也必须写 `recipient_evidence`。该字段是记录证据，不自行证明用户授权发送。

图灵派对的 `outlet` 为 `turing-party`，用户已在本次需求中指定投稿邮箱 `xuechaozou@foxmail.com`。同一任务沿用这一明确指定时，使用 `recipient_basis: "user_confirmed"`，并在 `recipient_evidence` 写明用户指定的地址与用途，不必重复询问地址。共享技能的其他使用者不能把本仓库作者的历史指定当成自己的确认；可自行核实或指定地址。无论哪种依据，仍须真实完成最终 Word 人工审核与当前邮件的发送确认。
- `blockers`: 未选目标、未确认署名、事实冲突、需要首发状态等实际未解决事项；有 blocker 可生成邮件预览但不能发送。仅删除确已解决的项，再重新 prepare。全文投稿缺少 Word 附件也会自动加入 blocker。
- `attachments`: 显式文件清单，不能用整个工作目录。总原始附件/正文上限 15 MiB。相同 basename 被拒绝。配图请逐个附件列出；大量图片可主动制作仅含公开图片的 ZIP。
- `from_email/from_name` 从配置读取，不在 job 覆盖。没有 SMTP 配置时使用不可投递的预览发件人并加入 blocker。

prepare 会拒绝覆盖已有包。正文和附件内容嵌入 `draft.eml`；原文后续编辑不会改变这个快照，应重新 prepare 到新目录。`review.json` 记录 SHA-256、收件人、主题、附件和 Message-ID。人工审核应针对该快照内的 Word 稿；用户明确确认后才用 record-approval 保存 human-approval.json。批准与邮件哈希绑定，改稿、改收件人、重新 prepare 后需要重新审核确认。不要把凭据放入正文，不伪造核验、用户确认或绕过 blocker。最初要求投稿不等于人工审核后的确认。

审核链接指向 `PACKAGE/attachments/稿件.docx`。程序在批准和发送前对照 MIME 快照、附件清单、实际审核附件与 `body.txt`；修改或移除包内 Word、正文、附件后会拒绝继续，必须从人工修改后的文件重建新包。其他目录的源文件不受快照校验监控，因此用户指定的外部修改稿也必须重新读取和打包。`.docx` 附件会检查基本 ZIP/XML 结构；这不替代 Word 排版、批注与科研内容的人工审核。

## 结果与重试

- `smtp-check`: 只连接、TLS、认证、退出，`mail_sent: false`。不发送测试邮件。
- `send` 无 `--execute`: 离线预览，完全不连接 SMTP。
- 实际投递成功：`receipt.json` 和 `~/.config/paper-wechat-submit/sent/<content-key>.json` 保存 `accepted_by_smtp`。只说明 SMTP 已接受，可能仍有后续退信。
- 连接/认证失败：无 DATA，可以修复后重试。异常只输出类型，避免服务器响应泄露凭据。
- DATA 期间失败：标记 `delivery_uncertain_do_not_retry`，保留 Message-ID，不自动重发。先让用户查发信服务商记录/退信。程序崩溃留下的 `connecting` 记录也不能盲目重发，先核对进程及服务商记录。
- 同内容、同发件人、同收件人、同主题再次执行会被持久日志拦截，即使重新 prepare 生成了不同 Date/Message-ID。用户明确要求重投且已排除重复风险时，人工核验后另行处理；不要自动删日志。

纯文本 SMTP 邮件负责说明来意，推文正文以 Markdown/HTML/必要的 Word 和原图附件供编辑处理。发送 HTML 附件时建议 render 加 `--embed-images`，把文章目录内的 PNG/JPEG/GIF/WebP 嵌入 HTML，避免单独打开时缺图；原图仍单独附上方便编辑。远程图片不会自动下载或嵌入。
