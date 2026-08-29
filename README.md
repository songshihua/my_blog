# SS·LAB 个人研究博客

这是一个前后端分离的个人研究主页与 AI 前沿雷达项目。前端按照提供的四张界面设计图实现，后端遵循 `宋世华个人博客_MySQL部署文档.md` 的 Django 5.2、MySQL 8.4、Docker 与 Nginx 基线。

当前阶段只面向本地开发。设计图中的论文、数字、趋势和性能曲线均以 `SAMPLE / DEMO / 示意数据` 标记，不会作为真实研究成果展示。

## 技术架构

- 前端：React 19、TypeScript、Vinext App Router、Tailwind CSS、shadcn 基础组件。
- 后端：Django 5.2、Django REST Framework、django-filter、OpenAPI。
- 数据库：MySQL 8.4，开发与生产保持同一数据库类型。
- 内容维护：Django Admin；公开 API 仅提供只读数据。
- 本地隔离：根目录 `.venv` 与 Docker MySQL；所有项目文件均位于 `D:\my_blog`。

## 页面

| 路由 | 内容 |
| --- | --- |
| `/` | 首页、研究方向、Inference Lab、近期笔记 |
| `/projects` | 项目筛选、投机解码/KV Cache/Serving 概念图 |
| `/notes` | 技术笔记列表 |
| `/notes/[slug]` | 三栏文章页、目录、进度、复制、收藏和分享 |
| `/radar` | AI 前沿搜索、筛选、摘要、收藏与来源状态 |
| `/about` | 个人简介与联系方式 |

## 第一次本地启动（推荐：虚拟环境 + Docker MySQL）

前置条件：Windows、Python 3.13、Node.js 22、Docker Desktop。

```powershell
Set-Location D:\my_blog
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

脚本会创建 `.env` 随机密钥、`.venv`、安装依赖、启动 MySQL、执行迁移并写入明确标记的本地演示数据。

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

- 前端：`http://127.0.0.1:3000`
- API：`http://127.0.0.1:8000/api/v1/`
- API 文档：`http://127.0.0.1:8000/api/docs/`
- 管理后台：`http://127.0.0.1:8000/admin/`
- 健康检查：`http://127.0.0.1:8000/health/live`、`/health/ready`

创建管理员：

```powershell
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
```

需要轮换本地 Django 与 MySQL 密钥时（不会删除数据库数据）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rotate-local-secrets.ps1
```

轮换后需重启正在运行的 Django 进程，使其重新加载 `.env`。

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

## 安全边界

- `.env`、数据库密码、GitHub/Hugging Face Token 和模型密钥不得提交 Git。
- 浏览器只读取 `NEXT_PUBLIC_*` 变量；其中不得放入任何私密 Token。
- 公开端没有注册、评论、投稿或匿名同步接口。
- AI 雷达同步只能通过后端 management command 运行。
- 生产服务器不公开 `3306` 和 `8000`，只由 Nginx 暴露 80/443。

更详细的边界与接口见 [架构说明](docs/architecture.md) 和 [API 说明](docs/api.md)。云端发布前还需替换域名、邮箱、证书路径，完成备份恢复演练与安全检查。
