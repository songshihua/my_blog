# API v1

所有公开接口只允许 `GET`、`HEAD`、`OPTIONS`，列表返回 DRF 分页结构。

| 接口 | 用途 |
| --- | --- |
| `GET /api/v1/home/` | 首页聚合：档案、精选项目、近期文章、雷达条目 |
| `GET /api/v1/profile/` | 个人档案 |
| `GET /api/v1/topics/` | 研究主题 |
| `GET /api/v1/projects/` | 项目列表与筛选 |
| `GET /api/v1/projects/{slug}/` | 项目详情 |
| `GET /api/v1/articles/` | 已发布文章列表 |
| `GET /api/v1/articles/{slug}/` | 文章详情 |
| `GET /api/v1/articles/{slug}/related/` | 相关文章 |
| `GET /api/v1/radar/items/` | 雷达条目 |
| `GET /api/v1/radar/sources/` | 来源状态 |
| `GET /api/v1/radar/stats/` | 可验证的数据库统计 |

常用查询参数：`search`、`ordering`、`page`、`page_size`，以及资源相关的 `category`、`topics__slug`、`source__source_type`、`kind`、`since`。

开发环境的 OpenAPI 文档位于 `/api/docs/`；生产环境默认不公开文档页面。
