# 架构说明

```text
Browser
  ├─ React/Vinext frontend :3000 ──(本机受控导入)──┐
  └─ /api/v1, /admin, /health
            │
            ▼
       Django/DRF :8000
       ├───────────────┐
       ▼               ▼
   MySQL 8.4    data/notes 私有源文件
```

外部数据同步始终由 Django 后端执行；本地前端按钮只负责触发受控任务：

```text
arXiv Atom API ─────────┐
GitHub REST API ────────┼─> provider 校验/规范化 ─> 幂等事务 ─> MySQL ─> 只读 API
Hugging Face Hub API ──┤       │
DeepSeek Responses API ┘       └─> IngestionRun 审计状态与计数
```

## 边界

- `frontend/` 只负责公开展示、筛选和设备本地交互，不持有服务端密钥。
- `backend/` 负责模型、校验、只读 API、Admin、健康检查和一次性采集任务。
- `apps/core` 管理个人档案与共享主题；`portfolio` 管理项目；`blog` 管理文章；`radar` 管理来源、条目和采集记录。
- 写操作只通过 Django Admin、受控 management command，以及仅限本地开发的雷达同步和笔记导入接口完成。
- 第一阶段没有公众账户、评论、Redis、Celery 或搜索集群。
- `apps/radar/providers` 隔离第三方协议；`SourceSynchronizer` 统一处理事务、稳定外部 ID、主题白名单、运行状态与错误收口。
- arXiv 使用官方 Atom API，查询语句与数量上限由服务端控制，浏览器不能提交任意查询。
- GitHub 使用官方 Repository Search 发现近期活跃且达到最低 Stars 的公开 AI 仓库，只生成 `RadarItem`。第三方发现不会写入代表个人作品集的 `Project`；搜索 top-N 也不被当作完整快照，因此不会因某个仓库暂时掉出结果而自动下架。
- Hugging Face 使用官方 SDK，仅查询模型/数据集元数据，不下载权重或数据集内容。
- DeepSeek 必须完成 `web_search` 并按 JSON Schema 返回结果；入库前再次检查发布日期、HTTPS 域名白名单和来源 URL。模型只负责发现与摘要，不被当作事实来源。

## 笔记存储与解析

- `Category.parent` 构成最多 8 层的邻接表分类树；数据库唯一约束保护名称和 slug，`PROTECT` 防止误删仍被引用的分类。
- `Article` 保存供公开页面渲染的规范化 Markdown；`ArticleSourceFile` 一对一保存原文件元数据、SHA-256、提取目录和私有存储引用。
- 原始字节写入 `data/notes/YYYY/MM/<random-uuid>.<ext>`。路径由服务端生成，不使用浏览器文件名，也不通过 Django `MEDIA_URL` 直接暴露。
- Markdown 要求 UTF-8；DOCX 在解析前限制 ZIP 路径、成员数、展开大小、压缩比、宏、嵌入对象及危险 XML；PDF 限制页数、加密状态和提取字符数。
- 正文通过 `react-markdown` 与 GFM 渲染，不启用原始 HTML；不可信图片不会被页面自动加载。原文件下载经文章权限范围内的 API 返回，并设置 `nosniff` 与 `no-store`。
- 首版同步提取属于有界本地工作流。扫描 PDF 不做 OCR，旧 `.doc` 需先转为 `.docx`，避免引入常驻任务队列和高风险转换服务。

## 环境

- `config.settings.development`：本机 API 与 CORS。
- `config.settings.test`：独立 MySQL 测试库。
- `config.settings.production`：强制显式密钥与域名，并由 Nginx 终止 TLS。

## 数据真实性

`seed_demo` 只创建带 `is_demo=true` 的幂等样例。性能曲线、趋势、论文和同步状态在接入可验证来源之前不得改成真实口吻。

真实同步条目统一为 `is_demo=false`。前端用 `LIVE / SAMPLE` 明确区分，并只对确实包含 `ai_summary` 的条目提供 AI 摘要面板。第三方失败不会回退成伪造的“成功”数据。

## 运行与安全

- 本地前端同步接口只在 development 开关启用时工作，并同时校验 loopback 地址与可信本地 Origin；production settings 强制关闭该入口。
- 本地笔记导入同样要求 development、显式开关、loopback 地址和可信 Origin；production settings 强制关闭，且上传大小在 Django 和解析器两层受限。
- 每次任务使用 MySQL named lock，避免相同任务并发执行；数据库唯一约束提供最终幂等保障。
- 前端入口固定同步 arXiv、GitHub、Hugging Face，并设置服务端数量上限和冷却时间；已隐藏的 DeepSeek/OpenReview 不会被按钮触发。
- 今日简报只把最近 7 天的非演示雷达记录交给 DeepSeek 做结构化编辑，不启用联网工具；模型引用的条目 ID 会在服务端重新校验，并缓存相同数据的生成结果以控制费用。
- Token/Key 只从后端环境变量读取，不保存到 `sync_state`、API 响应、SQL 文件或日志。
- GitHub Search 查询、回溯天数、最低 Stars、排序方式和单次数量均由服务端配置，浏览器不能提交任意搜索表达式。
- HTTP 重试次数、等待时间、单次条目数和外部文本长度均有上限。
- DeepSeek 来源只允许 `AI_RADAR_ALLOWED_DOMAINS` 中的 HTTPS 主机及其子域，重定向后会重新校验。
- 当前为一次性任务模型；云端应由 cron/平台调度器调用同一服务，不开放匿名触发接口。
