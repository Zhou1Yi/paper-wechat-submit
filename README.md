# Paper WeChat Submit

把论文链接转成适配目标公众号的中文 **Word 推文**，经过人工审核与明确确认后，再通过本地 SMTP 投稿。

这是一个 Codex Skill，支持机器之心、量子位、新智元、CVer、极市平台、我爱计算机视觉、PaperWeekly 和 VALSE。它用于论文宣传与公众号投稿，不是学术期刊投稿系统。

> **默认停在 Word 人工审核阶段。** 配置邮箱、验证登录或最初提出投稿需求，都不等于审核后的发送确认。没有当前邮件版本的人工确认记录，发送程序会拒绝投递。

## 工作流程

```text
论文 / arXiv / 项目页链接
           ↓
选择目标公众号，核实资料和投稿渠道
           ↓
生成 Word 推文、配图、来源记录和邮件草稿
           ↓
人工审核、修改或批注
           ↓
明确确认最终稿、收件人、主题及附件
           ↓
记录该版本的确认 → SMTP 投递 → 保存回执
```

## 能做什么

- 从论文或项目网页采集正文、资源链接、元信息和原图入口。
- 按不同公众号调整标题、导语、结构、技术深度与结尾。
- 导出可编辑的 Word 正文与表格，并嵌入论文配图；也支持 Markdown 和 HTML。
- 区分明确投稿邮箱、合作/咨询邮箱，以及无可靠邮箱的手动联系渠道。
- 在本地配置 SMTP，检查 TLS 与认证，凭据不进入技能仓库或投稿包。
- 为每次投稿生成固定的邮件、附件快照及 SHA-256 摘要。
- 拦截未确认投递、重复投递和结果不确定后的自动重发。

## 写作风格的实际能力

当前版本使用**平台写作指南与公开样文参考**，不是经过各公众号语料微调的模型，也不保证复现某个编辑或栏目的写作风格。

`references/writing.md` 中的篇幅、结构和语气主要是编辑建议；有来源的公开投稿规则另行标明。技能要求在实际任务中核实所选平台规则及相关文章，但目前尚未逐个平台完成多篇近期样文的系统校准。建议提供同栏目、相近主题的参考文章，以便进一步对齐标题、节奏、技术深度和配图方式。

科研事实优先于媒体表达：不能为贴合标题风格而虚构录用、首创、SOTA、速度或成本。性能比较应保留测试条件，区分百分比与百分点。

## 安装到 Codex

将本仓库克隆到个人技能目录。私有仓库需要你已有的 GitHub 访问权限：

```bash
git clone git@github.com:Zhou1Yi/paper-wechat-submit.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/paper-wechat-submit"
```

如果同名技能目录已存在，先检查已有版本，避免覆盖本地修改。技能入口为根目录的 `SKILL.md`。

### 依赖

- `scripts/submit.py`：Python 3.9+，只使用标准库。
- `scripts/export_docx.py`：Python 3.9+、`python-docx`、`Pillow`。
- Word 排版检查：使用 Codex 文档技能及其渲染工具，通常需要 LibreOffice、PDF 渲染工具和可用中文字体。
- Codex 负责论文理解和写作。脚本本身不会调用大模型生成文章，也不需要另配 LLM API key。

优先复用 Codex 提供的文档运行时；独立使用 Word 导出器时可以创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-docx.txt
```

## 在 Codex 中使用

**生成审核稿：**

```text
用 $paper-wechat-submit 读取 https://xavierjiezou.github.io/ARGUS/，
按机器之心的论文解读结构生成 Word 推文，供我人工审核，不要发送邮件。
```

**参考指定样文：**

```text
用 $paper-wechat-submit 把我的论文写成 PaperWeekly 推文。
参考我提供的同栏目文章，先生成 Word 供审核。
```

**人工修改后：**

```text
我已在 Word 中修改并添加批注。请以这份 Word 为准修订，
保留我的修改，重新给我审核，暂不投递。
```

真正投递前，需要你明确确认**最终 Word 版本、目标邮箱和邮件内容**。单纯说“稿子不错”或设置好 SMTP 不应当作发送确认。

## 支持的平台与渠道

下列为仓库中 2026-09-04 的核验记录；实际投稿前应重新核实。邮箱和规则可能变更。

| 平台 | 内置渠道 | 用途与证据 |
| --- | --- | --- |
| 机器之心 | liyazhou@jiqizhixin.com / zhaoyunfeng@jiqizhixin.com | 官方历史 AIxiv 文章明确列出投稿邮箱；每封邮件仅选一个收件人 |
| 量子位 | ai@qbitai.com | 官方投稿与爆料邮箱；主题应标注投稿或爆料 |
| 新智元 | daijia@aiera.com.cn / xiaoyunhong@aiera.com.cn | 官方合作邮箱，默认仅咨询 |
| CVer | 公众号后台等手动渠道 | 尚无可靠统一投稿邮箱 |
| 极市平台 | developer@cvmart.net | 官方联系邮箱，默认仅咨询 |
| 我爱计算机视觉 | amos@52cv.net | 历史署名内容与转载提供，正式投递前进一步核实或由用户确认 |
| PaperWeekly | hr@paperweekly.site | 第三方托管的署名文章提供，正式投递前进一步核实或由用户确认 |
| VALSE | valse_official@163.com | 会议官网联系邮箱，默认仅咨询 |

完整来源、证据等级和说明见 [outlets.json](references/outlets.json)。咨询邮件也遵循人工审核与明确确认流程。选择多个平台时分别写稿、分别发信，不群发或互相抄送。

## 配置本地 SMTP

在仓库根目录执行：

```bash
python3 scripts/submit.py init-config
python3 scripts/submit.py configure
python3 scripts/submit.py smtp-check
```

`configure` 在本机终端隐藏输入授权码。不要将密码或授权码贴进聊天、README、Issue 或命令行参数。

默认本地文件：

```text
~/.config/paper-wechat-submit/
├── smtp.json       # 服务器、发件人、凭据路径
├── smtp.secret     # 授权码，权限 0600
└── sent/           # 投递记录与重复投递检测
```

凭据文件是本机文件存储，不是加密保险库。也可通过配置 `password_env` 读取已有环境变量。支持隐式 TLS 或 STARTTLS 下的用户名/密码或授权码认证，尚不支持 OAuth-only 邮箱。

QQ 邮箱可使用 `smtp.qq.com`、465、`ssl`，用户名为完整邮箱地址，密码使用邮箱开启 SMTP 后生成的授权码。其他服务商参数应以官方说明为准。

`smtp-check` 只验证连接与登录，**不会发送测试邮件**。

## 脚本使用

```bash
# 查看平台列表
python3 scripts/submit.py outlets

# 保存网页资料；PDF 仅下载，需另行解析
python3 scripts/submit.py collect https://xavierjiezou.github.io/ARGUS/ \
  --out ./output/argus/sources

# 将已写好的 Markdown 导出为 Word
python3 scripts/export_docx.py ./output/argus/article.md \
  --out ./output/argus/article.docx

# 导出可单独阅读的 HTML；本地配图嵌入文件
python3 scripts/submit.py render ./output/argus/article.md \
  --out ./output/argus/article.html --embed-images

# 固定邮件和附件快照；不会发送
python3 scripts/submit.py prepare ./output/argus/job.json \
  --out ./output/argus/package-v1

# 离线检查邮件包；不会连接 SMTP
python3 scripts/submit.py send ./output/argus/package-v1
```

Word 导出后必须渲染并逐页检查，特别是中文字体、图片与表格。用户修改后的 Word 是下一轮修订依据，不应使用旧 Markdown 覆盖它。

### 投稿任务示例

`job.json` 中的文件路径相对该文件所在目录：

```json
{
  "outlet": "jiqizhixin",
  "mode": "submission",
  "to": "liyazhou@jiqizhixin.com",
  "recipient_basis": "registry",
  "subject": "【AIxiv 投稿】论文名称与具体贡献",
  "body_file": "email.txt",
  "attachments": ["article.docx", "article.md", "article.html"],
  "blockers": ["等待作者人工审核 Word 并确认最终内容"]
}
```

这里只是格式示意，不是已获准投递的任务。仅在实际问题解决后更新 `blockers`，然后重新准备邮件包。`registry` 模式会拒绝超过 30 天的核验记录；重新核实或用户明确确认地址时，按 [SMTP 说明](references/smtp.md) 记录依据。

### 审核确认后投递

仅在人工已审核最终 Word、解决所有待办并明确确认当前收件人和内容后，才执行：

```bash
python3 scripts/submit.py record-approval ./output/argus/package-v1 \
  --statement '记录用户审核后对这一最终版本明确确认发送的真实表述'

python3 scripts/submit.py send ./output/argus/package-v1 --execute
```

`record-approval` 是对真实人工确认的记录，不能伪造，也不能把程序检查当作人工审核。这是工作流保护，不是独立身份认证或防篡改签名系统。

批准记录绑定邮件快照；换稿、换收件人或重新生成邮件包后需重新审核确认。程序记录 `accepted_by_smtp` 只表示服务器接受，不等于最终送达或编辑录用。DATA 阶段结果不明时不自动重发，应按 Message-ID 查询服务商记录。

## 目录结构

```text
paper-wechat-submit/
├── SKILL.md
├── README.md
├── requirements-docx.txt
├── agents/openai.yaml
├── references/
│   ├── writing.md
│   ├── outlets.json
│   └── smtp.md
└── scripts/
    ├── submit.py
    ├── export_docx.py
    └── test_submit.py
```

## 验证

```bash
python3 scripts/test_submit.py
```

测试使用临时目录和模拟 SMTP，不访问外部邮件服务器。覆盖中文邮件、附件快照、离线预览、未确认拦截、错误渠道、凭据文件排除、重复投递以及发送结果不确定等场景。

## 当前限制

- 不是公众号官方插件，不保证符合未公开的编辑规范或获得录用。
- 网站可能需要登录或动态加载，采集结果需要人工/模型核对。
- Markdown 导出器仅支持本技能使用的简单格式，不是完整 Markdown 或复杂公式转换器。
- 稿件事实检查与人工审核不能被 SHA-256 校验代替。
- 本仓库不包含个人 SMTP 配置、授权码、人工批准记录、发信日志或本地生成的论文稿件。
