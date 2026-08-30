# API v1

公开内容接口只允许 `GET`、`HEAD`、`OPTIONS`。项目、文章和雷达条目列表返回 DRF 分页结构；雷达来源返回无分页数组，统计接口返回对象。本地开发另提供受限的雷达同步、笔记导入和笔记管理接口。

| 接口 | 用途 |
| --- | --- |
| `GET /api/v1/home/` | 首页聚合：档案、精选项目、近期文章、雷达条目 |
| `GET /api/v1/profile/` | 个人档案 |
| `GET /api/v1/topics/` | 研究主题 |
| `GET /api/v1/projects/` | 项目列表与筛选 |
| `GET /api/v1/projects/{slug}/` | 项目详情 |
| `GET /api/v1/articles/` | 已发布文章列表 |
| `GET /api/v1/articles/tree/` | 完整分类层级、已发布文章及本地导入能力状态 |
| `GET /api/v1/articles/{slug}/` | 文章详情 |
| `GET /api/v1/articles/{slug}/related/` | 相关文章 |
| `GET /api/v1/articles/{slug}/source-file/` | 下载该文章对应的原始 MD、DOCX 或 PDF 文件 |
| `POST /api/v1/articles/categories/` | 仅限可信本机前端，新建笔记目录 |
| `POST /api/v1/articles/import/` | 仅限可信本机前端，导入一个笔记文件并发布文章 |
| `DELETE /api/v1/articles/{slug}/manage/` | 仅限可信本机前端，删除一篇笔记文章 |
| `DELETE /api/v1/articles/categories/{slug}/` | 仅限可信本机前端，删除一个空目录 |
| `GET /api/v1/radar/items/` | 雷达条目 |
| `GET /api/v1/radar/sources/` | 来源状态 |
| `GET /api/v1/radar/stats/` | 可验证的数据库统计 |
| `POST /api/v1/radar/sync/` | 仅限可信本机前端，同步 arXiv、GitHub、Hugging Face |

常用查询参数：`search`、`ordering`、`page`、`page_size`，以及资源相关的 `category`、`topics__slug`、`source__source_type`、`kind`、`since`。

`Project` 只表示个人作品集；GitHub 公开搜索发现的第三方仓库不会写入该列表。`RadarItem` 列表包含 `is_demo`、可选 `ai_summary`，并为 GitHub 仓库显式返回安全的 `repository_metrics`（Stars、Forks、语言），不会直接暴露任意来源元数据。`RadarSource` 包含 `is_configured`、启用状态、最近尝试/成功/失败时间和最近条目数。所有这些字段都不包含 Token 或 Key。

开发环境的 OpenAPI 文档位于 `/api/docs/`；生产环境默认不公开文档页面。

`POST /api/v1/radar/sync/` 不接受来源、查询词、数量或凭据参数，所有范围均由服务端固定。它要求 development 模式、本地同步开关、loopback 客户端地址与允许的本地 `Origin` 同时满足，并带有 MySQL 跨进程锁和冷却时间。production settings 强制关闭该接口。

`POST /api/v1/articles/import/` 使用 `multipart/form-data`，字段为 `file`、`category_slug`，以及可选的 `title`、`summary`。服务端只接受 `.md` / `.markdown`、`.docx` 和 `.pdf`，校验声明类型、文件签名、解析边界和内容摘要；同一 SHA-256 的文件重复提交返回 `409`。成功返回完整文章详情并使用 `201`。接口要求 development 模式、`NOTE_BROWSER_IMPORT_ENABLED=True`、loopback 客户端地址与允许的本地 `Origin` 同时满足；production settings 强制关闭。

目录创建、文章删除和目录删除沿用相同的可信本机权限。删除文章会同时清理其源文件记录和私有源文件；目录删除仅允许空目录，若仍包含文章或子目录则返回 `409`。

文章列表与详情中的 `source_file` 仅包含原文件名、格式、大小和受控下载 URL，不返回磁盘绝对路径、随机存储名或 SHA-256。分类对象包含 `parent_slug` 与从根到父级的 `ancestors`，前端据此构建任意深度目录树。
