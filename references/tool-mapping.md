# 工具与脚本适配

## 优先使用环境中已连接的 MCP

下表来自原工作流使用的本地服务约定，不是所有小红书 MCP 都具有的统一接口。先看当前工具 schema，不能向不兼容工具硬传参数。

| 目的 | 本地服务工具约定 | 需要检查 |
|---|---|---|
| 登录状态 | `check_login_status` | 状态字段或登录提示 |
| 搜索 | `search_feeds(keyword, limit, filters)` | 数量、stop_reason、batches；是否支持 limit |
| 推荐流 | `list_feeds` | 只能当作推荐样本 |
| 详情和初始评论 | `get_feed_detail(feed_id, xsec_token)` | note / comments 的实际位置 |
| 扩展评论 | 详情工具的 `load_all_comments=true` | 实际 limit / max_comment_items、回复与 hasMore |
| 共享阅读器（可选） | `http://127.0.0.1:18060/reader` | 仅原集成支持，不是假定存在的公共站点 |

原服务的数据约定：搜索结果 `feeds[]` 含 `id`、`xsecToken` 和 `noteCard`；详情中笔记在 `data.note`，一级评论在 `data.comments.list`。`no_growth` 只表示连续等待未出现新 ID，不能证明结果已穷尽。

## 可选收集脚本

`scripts/research.py` 适用于接受单次 JSON 响应的 `/mcp` 本地网关，并依赖上面的数据约定。它不是通用 MCP 客户端：不处理 SSE 流式响应、初始化握手、协商会话或所有服务版本。如果网关不兼容，优先使用宿主提供的 MCP 工具，不猜测接口。

配置（不把实际凭据写入 skill）：

- `XHS_MCP_URL`：默认 `http://127.0.0.1:18060/mcp`。
- `XHS_MCP_TOKEN_FILE`：可选的本地 Bearer 凭据文件路径；未配置则不发送 Authorization。
- `XHS_READER_CATALOG`：可选的共享阅读器目录文件路径；未配置时只在输出目录生成目录。

```bash
python3 scripts/research.py --query "手冲咖啡 入门" --limit 30 --out ./work/coffee
```

`--query` 可重复；`--limit` 是每个关键词的检索上限，**不是全局目标数**。全局数量要求由宿主使用 MCP 筛选合并落实，不把该脚本的全部命中自动当成目标语料。`--details 0` 默认读全部命中；正数是明确的部分读取。不同 brief 用不同目录；相同配置自动恢复已完成操作，`--retry-partial` 重新搜索未达到目标的批次。

输出 `evidence.json`、`summary.json`、`reader-catalog.json`。summary 的 complete 仅指检索达到每词上限且已收集全部详情；它不等于研究完成。媒体、逐篇分析、外部核查另行记录。脚本没有自动回复扩展、创作者主页遍历或 brief JSON 执行能力。

## 可选媒体文字提取

```bash
python3 scripts/read_media.py --evidence ./work/coffee/evidence.json \
  --cache ./work/coffee/media-cache --ocr /path/to/ocr-executable
```

需要 Python 3.10+、PATH 中的 curl 和自行准备的 OCR 可执行程序。OCR 接受一个图片路径参数，在 stdout 输出 UTF-8 JSON：`{"lines": ["文字行"]}`。非零退出表示失败。工具本身没有打包 OCR 引擎，也不会调用大模型。

图片按内容及 OCR 程序更新时间缓存；下载原子完成。仅提取平台提供的可用字幕，不做语音识别、视频下载、场景切分或完整观看。结果在 `media.json`，分析判断另外保存。脚本缓存应与对应 evidence 配套，来源变化使用新的缓存目录。
