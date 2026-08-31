# SS·LAB 个人研究博客

这是一个前后端分离的个人研究主页与 AI 前沿雷达项目。前端按照提供的四张界面设计图实现，后端使用 Django 5.2 与 MySQL 8。当前本地开发默认连接 Windows MySQL80，不依赖 Docker 数据库。

当前阶段只面向本地开发。设计图中的论文、数字、趋势和性能曲线均以 `SAMPLE / DEMO / 示意数据` 标记，不会作为真实研究成果展示。

## 技术架构

- 前端：React 19、TypeScript、Vinext App Router、Tailwind CSS、shadcn 基础组件。
- 后端：Django 5.2、Django REST Framework、django-filter、OpenAPI。
- 数据库：MySQL 8.4，开发与生产保持同一数据库类型。
- 内容维护：Django Admin，以及受本机安全边界保护的前端笔记导入。
- 本地环境：根目录 `.venv` 与 Windows MySQL80；所有项目文件均位于 `D:\my_blog`。

## 页面

| 路由 | 内容 |
| --- | --- |
| `/` | 首页、研究方向、Inference Lab、近期笔记 |
| `/projects` | 项目筛选、投机解码/KV Cache/Serving 概念图 |
| `/notes` | 多级分类知识库、最近更新与前端笔记导入 |
| `/notes/[slug]` | 左侧分类树、正文阅读区、右侧自动目录与原文件下载 |
| `/radar` | AI 前沿搜索、筛选、摘要、收藏与来源状态 |
| `/about` | 个人简介与联系方式 |

## 第一次本地启动（虚拟环境 + Windows MySQL80）

前置条件：Windows、Python 3.13、Node.js 22，以及正在运行的 MySQL80 服务。

项目连接 `127.0.0.1:3306` 上的 `song_blog` 数据库。`.sql` 文件是一次性导入源，应用运行时不会直接读取它。首次使用或需要从备份恢复时执行：

```powershell
Set-Location D:\my_blog
powershell -ExecutionPolicy Bypass -File .\scripts\import-local-mysql.ps1
```

脚本默认导入 `backups\song_blog.sql`，会要求输入本机 MySQL 管理员密码，并按照 `.env` 创建或更新应用账号。密码只进入临时客户端配置，脚本结束后立即删除；导入会替换 `song_blog` 中同名的现有表，因此还需要输入 `IMPORT` 确认。

安装项目依赖：

```powershell
Set-Location D:\my_blog
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\development.txt -c backend\requirements\constraints.txt
Set-Location .\frontend
npm install
```

如果 `.venv` 尚不存在，请先运行 `python -m venv .venv`。现有 `scripts\setup.ps1` 是保留的 Docker 全自动初始化流程；使用本机 MySQL80 时不要运行它。

分别在两个终端启动：

```powershell
# 终端 1：Django API
Set-Location D:\my_blog
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

```powershell
# 终端 2：React 前端
Set-Location D:\my_blog\frontend
npm run dev
```

访问地址：

- 前端：`http://localhost:3000`
- API：`http://127.0.0.1:8000/api/v1/`
- API 文档：`http://127.0.0.1:8000/api/docs/`
- 管理后台：`http://127.0.0.1:8000/admin/`
- 健康检查：`http://127.0.0.1:8000/health/live`、`/health/ready`

创建管理员：

```powershell
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
```

## 笔记分类与前端文件导入

访问 `http://localhost:3000/notes`，可在左侧新建目录、添加笔记或打开“管理笔记”。上传时选择目标目录；管理窗口支持逐篇删除文章，并在目录为空且不包含子目录时删除目录。所有删除操作都有二次确认。

- 支持 UTF-8 编码的 `.md` / `.markdown`、Word `.docx` 和 `.pdf`（含扫描版）；PDF 可在原版视图与文本视图间切换。
- 暂不支持旧版 Word `.doc`；扫描版 PDF 暂不执行 OCR，应先在本地转换为可检索 PDF。
- 单文件默认不超过 8 MB；可通过后端环境变量 `NOTE_UPLOAD_MAX_BYTES` 下调，上限固定为 10 MB。
- 原文件保存在项目目录 `data/notes/YYYY/MM/`，数据库只保存文章、目录、校验摘要与随机文件路径。
- `data/notes` 默认被 Git 忽略，避免误把私人文档或大文件上传到 GitHub；需要版本控制的内容应先人工检查后再有选择地调整忽略规则。
- 分类最多 8 层；删除仍被文章或子目录使用的目录会被前后端共同阻止，避免误删整棵目录。

该导入接口只在 development、loopback 地址和可信本地前端 Origin 同时满足时开放，`production` 配置会强制关闭。相关配置位于根目录 `.env`：

```dotenv
NOTE_BROWSER_IMPORT_ENABLED=True
NOTE_UPLOAD_MAX_BYTES=8388608
```

拉取包含此功能的新代码后，执行依赖安装和数据库迁移，再重启前后端：

```powershell
Set-Location D:\my_blog
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\development.txt -c backend\requirements\constraints.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
Set-Location .\frontend
npm install
```

需要轮换本地 Django 与 MySQL 密钥时（不会删除数据库数据）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rotate-local-secrets.ps1
```

轮换后需重启正在运行的 Django 进程，使其重新加载 `.env`。
密钥轮换脚本仍用于 Docker 模式；本机 MySQL80 模式下不要运行它。

如果 `.env` 已被错误内容覆盖，导致当前 MySQL 密码也无法再连接，可使用应急恢复脚本。它只重置 `song_blog` 本地数据卷中的数据库账号并重新生成本地密钥，不删除数据卷：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\recover-mysql-access.ps1 `
    -ConfirmDataPreservingReset
```

该脚本仅用于本地开发故障恢复；云端数据库应使用云厂商的密钥轮换与审计流程。

## 本机 MySQL80 管理

本机 MySQL 默认监听 `127.0.0.1:3306`。数据库账号和密码保存在本机 `.env`，不要把密码写入 SQL、命令历史或 Git。Navicat 应连接同一地址，并展开 `song_blog` 数据库。

在 Navicat 中连接 `127.0.0.1:3306`，选择 `.env` 中 `MYSQL_DATABASE` 对应的数据库后，再打开 [`deploy/mysql/local-management.sql`](deploy/mysql/local-management.sql)。该文件默认运行在只读事务中，包含表规模、内容数量、同步状态、最近采集记录和索引检查，不包含任何凭据。

迁移完成后，可生成不含数据和密码的数据库结构快照：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\export-database-schema.ps1
```

输出文件为 [`deploy/mysql/schema.sql`](deploy/mysql/schema.sql)。Django migrations 仍是结构变更的唯一事实来源；请勿直接编辑快照或在数据库中手工改表。完整数据备份与恢复演练应使用独立备份流程，结构快照不能替代数据备份。

## 全 Docker 本地启动

```powershell
Copy-Item .env.example .env
# 先修改 .env 中的三个 replace-* 值
docker compose -f compose.yaml -f compose.dev.yaml build
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python manage.py migrate
docker compose -f compose.yaml -f compose.dev.yaml run --rm backend python manage.py seed_demo
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

不要执行 `docker compose down -v`；它会删除 MySQL 数据卷。

## 常用开发命令

```powershell
# Django 系统检查与迁移漂移检查
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run

# 后端测试（使用独立 song_blog_test）
.\.venv\Scripts\python.exe -m pytest backend\tests

# 手工运行雷达任务；没有配置来源时会明确跳过，不会伪造同步成功
.\.venv\Scripts\python.exe backend\manage.py ingest_sources --dry-run

# 前端质量检查
Set-Location frontend
npm run lint
npm run typecheck
npm run build
```

## arXiv、GitHub、Hugging Face 与 DeepSeek 同步

所有第三方凭据只放在根目录 `.env`，并且只由 Django 后端读取。先按需要配置：

```dotenv
# arXiv 默认根据 AI_RADAR_KEYWORDS 查询；如需高级查询可填写官方查询语法
ARXIV_SEARCH_QUERY=

# GitHub 公开 AI 项目发现：不读取个人仓库；Token 可选但建议配置以提高搜索限额
GITHUB_TOKEN=
GITHUB_DISCOVERY_QUERY=llm
GITHUB_DISCOVERY_LOOKBACK_DAYS=30
GITHUB_DISCOVERY_MIN_STARS=20
GITHUB_DISCOVERY_SORT=stars

# Hugging Face：作者和搜索词至少填写一个；公开元数据无需 Token
HUGGINGFACE_AUTHOR=
HUGGINGFACE_SEARCH=llm inference
HUGGINGFACE_TOKEN=

# DeepSeek：必须填平台生成的真实 API Key；联网检索会产生 API 费用
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
```

保存 `.env` 后请重启正在运行的 Django 开发服务器；环境变量只在进程启动时加载。

本地开发时，`/radar` 页面的“立即同步”按钮会同步 arXiv、GitHub 与 Hugging Face，结束后自动刷新来源状态、统计和条目。按钮不会调用界面已隐藏的 DeepSeek/OpenReview；服务端具有防并发锁和 30 秒冷却。production settings 会强制关闭该本地入口，云部署时应改用平台定时任务或带身份认证的管理入口。

单独验证和同步每个来源：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-radar.ps1 -Source github -Limit 50
powershell -ExecutionPolicy Bypass -File .\scripts\sync-radar.ps1 -Source huggingface -Limit 10
powershell -ExecutionPolicy Bypass -File .\scripts\sync-radar.ps1 -Source arxiv -Limit 20
powershell -ExecutionPolicy Bypass -File .\scripts\sync-radar.ps1 -Source deepseek -Limit 3
```

也可以在 Django Admin 的“雷达来源”中启用需要定时执行的来源，再运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-radar.ps1 -Source all -Limit 20
```

显式指定 `-Source` 可用于手工验证，即使该来源尚未启用；`-Source all` 只运行后台已启用的来源。同步使用来源稳定 ID 幂等更新，重复运行不会制造重复雷达条目。GitHub 使用官方 Repository Search，从公开、未归档、最近有提交的 AI/LLM 仓库中按 Stars 排序；这些第三方发现只进入研究雷达，不会冒充“我的项目”。当前 Stars 是同步时的总量，不代表近期涨星趋势。Hugging Face 只读取模型/数据集元数据，DeepSeek 的结果还会经过日期、域名白名单和来源 URL 校验。未配置、限流或响应不可验证时会记录为跳过/失败，不会伪造内容。

## 安全边界

- `.env`、数据库密码、GitHub/Hugging Face Token 和模型密钥不得提交 Git。
- 浏览器只读取 `NEXT_PUBLIC_*` 变量；其中不得放入任何私密 Token。
- 公开端没有注册、评论、投稿或生产环境匿名同步接口。
- 本地前端同步仅接受可信 loopback 与本地 Origin；生产配置强制关闭，云端使用受控任务。
- 生产服务器不公开 `3306` 和 `8000`，只由 Nginx 暴露 80/443。

更详细的边界与接口见 [架构说明](docs/architecture.md) 和 [API 说明](docs/api.md)。云端发布前还需替换域名、邮箱、证书路径，完成备份恢复演练与安全检查。
生产 settings 会拒绝占位密钥、弱密钥、缺少真实域名、非 HTTPS CSRF 来源、弱数据库密码以及关闭 SSL/HSTS 的配置。
