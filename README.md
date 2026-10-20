# 小红书研究工作流 · xhs-research-workflow

把“帮我搜一下小红书”变成一套有来源、有阅读覆盖、有判断的研究流程。

这套 skill 整理自实际使用的小红书调研工作流：确定问题 → 多关键词搜索 → 去重 → 逐篇读正文/图片文字/可用字幕/评论 → 综合经验与反例 → 输出可行动结论。

## 它适合做什么

- 买东西前：比较具体产品版本、用户场景、换用原因和踩坑体验。
- 学习一个主题：归纳方法、资源、执行成本与真实结果。
- 研究创作者：梳理系列内容、观点变化、后续更正。
- 做内容选题：从讨论、争议与未满足需求提炼草稿。

特点是默认阅读全部选定笔记，区分“提到 / 用过 / 推荐”，保留负面与无效体验；图片 OCR、视频字幕、画面和评论分别记录覆盖，避免把“抓到数据”写成“分析完成”。结果先回答问题，过程材料作为依据。

## 从零开始：先装 MCP，再装 Skill

这份指南面向**在自己电脑上运行 Codex 的用户**。手机需要已登录的小红书 App，用来扫码；电脑需要能访问 GitHub 下载页面。浏览器第一次启动会额外下载运行文件，可能需要等待。

这里使用公开上游 [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)，不是小红书官方产品。下面的文件名已按 [v2.5.5 发布页](https://github.com/xpzouying/xiaohongshu-mcp/releases/tag/v2.5.5) 核对；其他版本以对应发布说明为准。

### 1. 下载 MCP 和登录工具

打开发布页，在 **Assets** 下载与你的电脑对应的**两个文件**，放到同一个新文件夹，例如“文稿 / xhs-mcp”。不要把账号运行目录放进本 skill 仓库。

| 电脑 | MCP 服务 | 登录工具 |
|---|---|---|
| Mac，Apple 芯片（M 系列） | `xiaohongshu-mcp-darwin-arm64` | `xiaohongshu-login-darwin-arm64` |
| Windows，Intel/AMD 64 位 | `xiaohongshu-mcp-windows-amd64.exe` | `xiaohongshu-login-windows-amd64.exe` |
| Linux，x64，有桌面环境 | `xiaohongshu-mcp-linux-amd64` | `xiaohongshu-login-linux-amd64` |

Mac 可在“关于本机”看芯片型号。当前发布没有 Intel Mac 或 Linux ARM64 的预编译文件；这两种情况先看[上游安装文档](https://github.com/xpzouying/xiaohongshu-mcp#readme)，不要下载不匹配的文件。

### 2. 在电脑上扫码登录

**Mac（Apple 芯片）**：打开“终端”。假设两个文件放在“文稿 / xhs-mcp”，逐行执行：

```bash
cd "$HOME/Documents/xhs-mcp"
chmod +x xiaohongshu-login-darwin-arm64 xiaohongshu-mcp-darwin-arm64
export COOKIES_PATH="$PWD/cookies.json"
./xiaohongshu-login-darwin-arm64
```

**Windows**：在保存文件的文件夹内，右键选择“在终端中打开”，使用 PowerShell 执行：

```powershell
$env:COOKIES_PATH = Join-Path (Get-Location) 'cookies.json'
.\xiaohongshu-login-windows-amd64.exe
```

登录工具会打开浏览器。用手机小红书 App 扫描页面上的二维码并确认，等待工具提示登录成功、保存登录状态后退出。二维码过期就重新运行登录工具。`cookies.json` 是本机登录状态，不要发给别人或上传 GitHub。

### 3. 启动 MCP 服务，保持终端开启

登录工具退出后，在**同一个终端、同一个文件夹**执行对应命令：

Mac：

```bash
./xiaohongshu-mcp-darwin-arm64 -port 127.0.0.1:18060 -headless=false
```

Windows PowerShell：

```powershell
.\xiaohongshu-mcp-windows-amd64.exe -port 127.0.0.1:18060 -headless=false
```

这里将服务绑定到本机。看到服务启动日志且终端持续运行即可；`http://127.0.0.1:18060/mcp` 是给 Codex 连接的协议地址，**不是普通网页**，不以浏览器能否显示页面来判断成功。

Linux x64 的步骤相同：给两个 Linux 文件执行权限，设置 `COOKIES_PATH` 后先运行 login，再运行 mcp，使用相同的 `-port` 和 `-headless=false` 参数。无桌面服务器的登录与容器部署请按[上游说明](https://github.com/xpzouying/xiaohongshu-mcp#readme)操作。

### 4. 把 MCP 连接到 Codex

以下两种方法选一种。连接在电脑上的 Codex 本地环境中使用；云端执行环境不能通过这个地址访问你电脑。

**方法 A：编辑配置，不需要另外安装 Codex CLI。** 打开 Codex 配置文件，默认路径为 `~/.codex/config.toml`（Windows 为用户目录下 `.codex/config.toml`）。若自定义过 `CODEX_HOME`，使用该目录内的 `config.toml`。文件或目录不存在时先创建；使用纯文本编辑器保存为 UTF-8。保留已有设置，新增下面这一段；同名配置已经存在时修改原段，不要重复添加：

```toml
[mcp_servers.xiaohongshu]
url = "http://127.0.0.1:18060/mcp"
tool_timeout_sec = 180
enabled_tools = ["check_login_status", "get_login_qrcode", "list_feeds", "search_feeds", "get_feed_detail", "user_profile", "get_my_profile"]
```

上面只开放本研究流程需要的登录和读取工具。

**方法 B：电脑已有 `codex` 命令时**，在另一个终端执行：

```bash
codex mcp add xiaohongshu --url http://127.0.0.1:18060/mcp
codex mcp list
```

方法 B 只负责添加连接；若也要限定工具范围，添加后在同名配置段补入方法 A 的 `enabled_tools` 和超时设置。

保存后重启 Codex，保持 MCP 服务终端运行。配置方式依据 [OpenAI 官方 MCP 文档](https://developers.openai.com/codex/mcp)。**小红书扫码发生在第 2 步的登录工具中**，不使用 `codex mcp login` 代替。

### 5. 确认登录和读取都能用

在 Codex 新会话中发送：

```text
请调用小红书 MCP 的 check_login_status 检查登录。
如果已登录，搜索“手冲咖啡 入门”，按工具实际能力取少量结果，
再选一篇读取正文和默认返回的评论，给我标题、原文链接和实际评论数。
这次只验证读取，不发布、不点赞、不收藏、不关注。
```

成功标志：工具报告已登录，搜索返回笔记，至少一篇详情能读到正文；评论可能为零或不可用，应按实际结果说明。仅在 MCP 列表看到服务器名称，还不代表小红书登录和详情读取已成功。

如果未登录，先在服务终端按 `Ctrl+C` 停止服务，重新执行第 2 步，成功后再执行第 3 步。不要在多个浏览器网页端反复登录同一账号；上游提醒这可能导致已有网页会话失效。

### 6. 安装 Skill

本仓库根目录就是一个 skill，目录名保持 `xhs-research-workflow`。把整个目录复制到 `~/.codex/skills/`，或在 Mac / Linux 且已安装 Git 时运行下面的命令（Windows 可使用下方 ZIP 安装方法）：

```bash
git clone https://github.com/longcc23/xhs-research-workflow.git "${CODEX_HOME:-$HOME/.codex}/skills/xhs-research-workflow"
```

目标目录如果已经存在，先检查已有内容再更新。没有 Git 的话，在本仓库页面点 **Code → Download ZIP**，解压后把目录改名为 `xhs-research-workflow`，放入用户目录下的 `.codex/skills/`（自定义 `CODEX_HOME` 时放到其 `skills/` 下）。确保最终路径为 `skills/xhs-research-workflow/SKILL.md`，中间不要多套一层目录。安装后在新会话中调用 `$xhs-research-workflow`。

## 第一次怎么用

直接发给 Codex：

```text
使用 $xhs-research-workflow，帮我研究小红书上新手手冲咖啡的常见问题。
目标 30 篇去重笔记，图文和视频都看，每篇先读默认评论。
告诉我大家最常卡在哪、哪些方法有人说有效、有哪些相反经验。
结论附原文来源，并说明图片、视频和评论实际读到了多少。
```

也可以换成产品比较、学习方法或某位创作者；涉及创作者时提供主页链接，涉及产品时给出型号和使用情境。

## 以后每次使用

登录状态有效时，不用每天重新扫码。重启电脑或关闭终端后，需要重新启动 MCP：进入保存程序的文件夹，设置第 2 步的 `COOKIES_PATH`，再执行第 3 步的服务命令，随后打开 Codex。用完在服务终端按 `Ctrl+C` 停止。

## 常见问题

| 遇到的情况 | 处理方法 |
|---|---|
| Mac 提示无法验证开发者 / 阻止打开 | 确认来自上游 Releases 后，按 macOS“系统设置 → 隐私与安全性”中的提示允许该程序，再运行；不需要关闭整机安全保护。 |
| Windows 拦截程序 | 确认下载来源和文件名，再按 Windows 给出的允许运行流程处理；不关闭全局安全防护。 |
| `codex` 命令不存在 | 使用第 4 步的方法 A。 |
| 提示 connection refused / MCP 无法连接 | 确认服务终端仍运行、端口与配置一致，且 Codex 在同一台电脑本地执行。 |
| 提示端口已占用 | 检查是否已启动一份 MCP；已有服务可用就复用。若改端口，启动命令与 Codex URL 同时修改。 |
| 扫码成功但仍显示未登录 | 确认 login 和 mcp 使用同一个绝对 `COOKIES_PATH`；按停止服务 → 重新扫码 → 重新启动的顺序操作。 |
| 第一次启动很久 / 浏览器下载失败 | 查看终端下载报错，确认网络后重试，不要反复扫码解决下载问题。 |
| 搜索不满 30 篇、部分内容读不到 | 以当前 MCP 的实际字段和返回数量为准。分关键词去重补充，并报告缺口，不能声称已完整读取。 |
| `/reader` 打不开 | 这是原工作区的定制功能，上游安装不保证提供；让 Codex 给出原文链接即可。 |

## 上游安装版与原工作区的区别

**Skill 提供研究方法，MCP 提供读取能力。** 原工作区使用带本地修改的服务，包含共享阅读器、检索扩展等增强；本指南使用公开上游版，不承诺复现这些功能。搜索上限、滚动、返回字段和评论展开能力必须看实际工具 schema。

先通过 Codex 的 MCP 工具完成研究即可。仓库内 `scripts/research.py` 是原 JSON 网关的可选适配脚本，**不要直接把它当成上游通用客户端**；媒体脚本还需要独立 OCR 程序。详见[工具适配说明](references/tool-mapping.md)。安装 MCP 本身不等于具备完整视频观看或 OCR 能力，缺失覆盖需如实标记。

没有 MCP 时也可以分析用户提供的导出材料，但不能声称进行了实时搜索。

## 文件

| 文件 | 用途 |
|---|---|
| [SKILL.md](SKILL.md) | 完整研究方法与边界 |
| [references/tool-mapping.md](references/tool-mapping.md) | MCP 约定、可选脚本与覆盖含义 |
| `agents/openai.yaml` | Codex 展示信息 |
| `scripts/research.py` | 可恢复的只读检索与详情采集 |
| `scripts/read_media.py` | 图片 OCR 和可用平台字幕提取 |

公开包不包含账号凭据、个人研究语料或登录态。研究默认只读，不自动发帖、点赞、收藏、评论或关注。社交经验用于理解讨论，医疗等关键建议需要权威来源核查。

此版本基于已有本地 skill 整理，改用可配置连接和可选阅读器目录；未将原有私有工具项目一并公开。
