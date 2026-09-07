# Paper WeChat Submit

把论文链接转成适配目标公众号的中文 **Word 推文**，经过人工审核与明确确认后，再通过本地 SMTP 投稿。

这是一个 Codex Skill，支持机器之心、量子位、新智元、CVer、极市平台、我爱计算机视觉、PaperWeekly、VALSE 和图灵派对。它用于论文宣传与公众号投稿，不是学术期刊投稿系统。

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
- 在论文信息旁展示作者与机构，合理安排方法图和实验截图；图片有引导、结果有解释，正文保留可见的完整资源网址。
- 区分明确投稿邮箱、合作/咨询邮箱，以及无可靠邮箱的手动联系渠道。
- 在本地配置 SMTP，检查 TLS 与认证，凭据不进入技能仓库或投稿包。
- 为每次投稿生成固定的邮件、附件快照及 SHA-256 摘要。
- 拦截未确认投递、重复投递和结果不确定后的自动重发。

## 按公众号调整写法

选择平台后，技能会调整标题、导语、章节顺序、技术深度、图表安排和结尾。你也可以提供同栏目参考文章，进一步对齐目标读者和表达方式。

| 平台 | 内容结构与写作重点 |
| --- | --- |
| [机器之心](references/styles/jiqizhixin.md) | 从研究问题切入，交代团队和核心结果，依次解释方法、数据、训练与实验证据。 |
| [量子位](references/styles/qbitai.md) | 用场景或疑问吸引阅读，先讲方法直觉，再展开关键机制、训练与结果。 |
| [新智元](references/styles/aiera.md) | 用导读概括亮点，以问题式小标题串联研究背景、方案与意义。 |
| [CVer](references/styles/cver.md) | 论文资源靠前，集中解释模块、输入输出、训练和消融，保留 CV 技术细节。 |
| [极市平台](references/styles/cvmart.md) | 侧重系统设计、评测条件与使用边界；复现教程另附环境、命令和实测记录。 |
| [我爱计算机视觉](references/styles/52cv.md) | 用直觉和方法图解串起研究设计、实验结果与技术点评。 |
| [PaperWeekly](references/styles/paperweekly.md) | 完整展开动机、设计、训练目标、评测协议、消融与局限，强调论证过程。 |
| [VALSE](references/styles/valse.md) | 默认准备研究分享提案、讲解提纲及论文资源；按栏目要求补充作者视频和摘要。 |
| [图灵派对](references/styles/turing-party.md) | 采用问题引入、方法图解、实验证据与讨论的研究解读结构。 |

各平台指南提供结构、图文安排和来源说明。共同排版建议包括：论文信息旁放作者与机构截图；对比图在问题说明后出现；流程图跟随模块介绍；实验截图后紧接结果分析。标题、格式和篇幅可按作者要求调整。

风格适配依据公开样文或编辑建议，不代表公众号官方模板。部分资料来自转载或历史栏目；机器之心指南参考作者审定稿，图灵派对参考链接暂未取得可读正文。详细依据见[写作指南](references/writing.md)及各平台档案。

每份稿件可附独立的写作对照说明，便于检查采用了哪些参考、如何组织内容。事实核对始终优先：团队、发表状态、模型名称及实验结果须有来源，性能比较保留测试条件。

## 安装到 Codex

将本仓库克隆到个人技能目录：

```bash
git clone https://github.com/Zhou1Yi/paper-wechat-submit.git \
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

**换公众号或比较版本：**

```text
用 $paper-wechat-submit 将 ARGUS 分别按量子位和 PaperWeekly 档案改写，
各生成一份 Word 和风格对照说明，供人工审核，不发送。
```

选择其他平台会重新安排导语、章节和技术解释。VALSE 默认是研究分享提案与讲解提纲，需要完整长文时会另附扩展解读。无可靠投稿渠道也能先完成 Word。

**人工修改后：**

```text
我已在 Word 中修改并添加批注。请以这份 Word 为准修订，
保留我的修改，重新给我审核，暂不投递。
```

真正投递前，需要你明确确认**最终 Word 版本、目标邮箱和邮件内容**。单纯说“稿子不错”或设置好 SMTP 不应当作发送确认。

## 支持的平台与渠道

选择平台即可使用以下联系渠道。邮箱和接稿要求可能变化，正式投递前需确认地址与稿件类型匹配。

| 平台 | 联系渠道 | 投稿说明 |
| --- | --- | --- |
| 机器之心 | z@jqzx.ai | AIxiv 学术与技术内容投稿；[栏目入口](https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzA3MzI4MjgzMw==&scene=1&album_id=4328536051397804037&count=3#wechat_redirect)。 |
| 量子位 | ai@qbitai.com | 投稿与爆料；邮件主题注明“投稿”或“爆料”。 |
| 新智元 | daijia@aiera.com.cn / xiaoyunhong@aiera.com.cn | 合作联系邮箱；先咨询报道需求与接稿方式。 |
| CVer | 公众号后台 | 通过后台联系编辑，确认投稿入口。 |
| 极市平台 | developer@cvmart.net | 官方联系邮箱；先咨询技术内容投稿的对接方式。 |
| 我爱计算机视觉 | amos@52cv.net | 投稿联系；投递前确认邮箱仍接收稿件。 |
| PaperWeekly | hr@paperweekly.site | 投稿联系；确认当前接稿要求及配图、辅助文件格式。 |
| VALSE | valse_official@163.com | 官方联系邮箱；先咨询研究分享的接收范围与材料形式。 |
| [图灵派对](https://mp.weixin.qq.com/s/kx3WiogHaDWHVBH86KZMoQ) | xuechaozou@foxmail.com | 投稿联系；使用前确认接收范围与稿件要求。 |

合作和一般联系邮箱默认用于咨询，确认接稿方式后再准备全文投递。部分投稿地址尚需官方复核或投稿者确认，来源和核对日期见[渠道资料](references/outlets.json)。咨询邮件同样需要人工确认；多平台投稿分别准备、分别发送。

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
  "to": "z@jqzx.ai",
  "recipient_basis": "registry",
  "subject": "【AIxiv 投稿】论文名称与具体贡献",
  "body_file": "email.txt",
  "attachments": ["article.docx"],
  "blockers": ["等待作者人工审核 Word 并确认最终内容"]
}
```

这里只是格式示意，不是已获准投递的任务。仅在实际问题解决后更新 `blockers`，然后重新准备邮件包。`registry` 模式会拒绝超过 30 天的核验记录；重新核实或用户明确确认地址时，按 [SMTP 说明](references/smtp.md) 记录依据。

### 投稿信

投稿信简要说明选题、稿件标题和附件，按编辑需要补充作者及联系方式。附件说明使用：

> 稿件 Word 版本随信附上。

人工审核、批准记录和校验状态属于本地工作流程，不写入给编辑的邮件正文。Markdown、HTML 和单独配图仅在需要时作为补充附件。完整说明见 [SMTP 与投稿信指南](references/smtp.md)。

### 审核确认后投递

仅在人工已审核最终 Word、解决所有待办并明确确认当前收件人和内容后，才执行：

```bash
python3 scripts/submit.py record-approval ./output/argus/package-v1 \
  --statement '记录用户审核后对这一最终版本明确确认发送的真实表述'

python3 scripts/submit.py send ./output/argus/package-v1 --execute
```

`record-approval` 是对真实人工确认的记录，不能伪造，也不能把程序检查当作人工审核。这是工作流保护，不是独立身份认证或防篡改签名系统。

批准记录绑定邮件快照；换稿、换收件人或重新生成邮件包后需重新审核确认。程序记录 `accepted_by_smtp` 只表示服务器接受，不等于最终送达或编辑录用。DATA 阶段结果不明时不自动重发，应按 Message-ID 查询服务商记录。

人工审核使用邮件包 `attachments/` 里的 Word。程序会检查它和实际邮件附件完全一致；人工修改后原包会被拒绝批准或发送，需读取修改稿并准备新包。修改包外的其他副本不会自动更新快照，请在确认时指明最终 Word。程序也会拒绝把普通文件改名为 `.docx` 的无效附件。

## 目录结构

```text
paper-wechat-submit/
├── SKILL.md
├── README.md
├── requirements-docx.txt
├── agents/openai.yaml
├── references/
│   ├── writing.md
│   ├── styles/  # 九个平台的写作指南与来源范围
│   ├── calibration-2026-09-06.md
│   ├── outlets.json
│   └── smtp.md
├── argus-machine-heart/  # 公开论文素材与参考稿
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
- 公开参考稿位于 `argus-machine-heart/`；个人 SMTP 配置、授权码、审核记录和发信日志应仅保存在本地。
