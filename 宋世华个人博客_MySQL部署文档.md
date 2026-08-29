# 宋世华个人博客与 AI 前沿雷达：MySQL 部署文档

> 适用项目：个人主页、技术博客、项目展示、AI 论文/文章聚合后台  
> 推荐技术栈：Django 5.2 LTS + MySQL 8.4 LTS + Gunicorn + Nginx + Docker Compose  
> 目标环境：Windows 开发机；Ubuntu 24.04 LTS 云服务器  
> 文档版本：2026-08-29

---

## 1. 最终方案

第一版建议使用一台云服务器，不单独购买托管数据库：

```text
浏览器
  │ HTTPS :443
  ▼
Nginx 容器
  ├─ /static/ ──► Django 静态文件
  ├─ /media/  ──► 用户上传文件
  └─ 其他请求 ──► Gunicorn + Django 容器
                         │
                         ▼
                    MySQL 8.4 容器

systemd timer ──► 一次性 Django 任务容器 ──► arXiv / GitHub / Hugging Face 等 API
systemd timer ──► mysqldump + media 备份 ──► 服务器外的备份位置
```

这套方案的特点：

- 开发和生产都直接使用 MySQL，不需要从 SQLite 迁移。
- MySQL、Django 和 Nginx 相互隔离，换服务器时容易搬迁。
- 服务器公网只开放 `80`、`443` 和受限的 `22`，不开放 MySQL 的 `3306`。
- AI 信息采集复用 Django 代码，但以一次性任务容器运行，不与 Web 请求混在同一进程。
- 第一版不需要 Redis、Celery、Kubernetes，也不需要 GPU。

推荐服务器规格：

- 只做博客和每日少量采集：`2 vCPU + 2 GB RAM + 40 GB SSD`。
- 同机做较多 AI 摘要、图片处理或高频采集：优先 `2 vCPU + 4 GB RAM + 60 GB SSD`。
- 如果服务器只有 2 GB 内存，可添加 1–2 GB swap，但 swap 不能替代内存。

本文中的示例值必须替换：

| 示例 | 替换为 |
|---|---|
| `blog.example.com` | 你的正式域名 |
| `www.blog.example.com` | 你的 `www` 域名；不用则删除 |
| `config.wsgi` | Django 项目真实的 WSGI 模块 |
| `<repository-name>` | 你的 GitHub 仓库名 |
| `your-email@example.com` | 申请证书使用的邮箱 |

---

## 2. 上线前准备

### 2.1 需要的账号与资源

- GitHub 仓库，例如 `https://github.com/songshihua/<repository-name>`。
- 一个域名。
- 一台 Ubuntu 24.04 LTS 云服务器，带公网 IPv4。
- 用于采集内容的 API Token，例如 GitHub Token；需要 AI 摘要时再准备模型 API Key。
- 一个服务器之外的备份位置，例如另一台电脑、对象存储或另一台服务器。

MySQL Community、Django、Gunicorn、Nginx 和 Docker 都可免费使用。实际费用来自云服务器、域名、对象存储、流量和第三方 AI API。

### 2.2 中国内地服务器注意事项

如果服务器位于中国内地并使用域名对外提供网站：

1. 域名先完成实名认证，个人备案时域名持有者应为本人。
2. 在服务器所属云厂商提交 ICP 备案。
3. 备案通过后再把域名解析到内地服务器并正式开放网站。
4. 网站底部展示备案号，并链接到工信部备案系统。
5. 网站开通后按要求办理公安联网备案。

个人站建议定位为“个人技术博客、研究笔记和论文索引”，第一版不要开放公众注册、公众发帖或做成新闻门户。

如果先部署到中国香港或海外服务器，通常不需要 ICP 备案，但中国内地访问速度和稳定性可能受跨境网络影响。

---

## 3. 建议的项目目录

下面假设 Django 项目包名为 `config`：

```text
song-blog/
├─ manage.py
├─ config/
│  ├─ settings.py
│  ├─ urls.py
│  └─ wsgi.py
├─ portfolio/
├─ blog/
├─ radar/
├─ templates/
├─ requirements.txt
├─ Dockerfile
├─ compose.yaml
├─ compose.prod.yaml
├─ .dockerignore
├─ .env.example
├─ deploy/
│  ├─ nginx/
│  │  ├─ http.conf
│  │  └─ https.conf
│  ├─ certbot/
│  │  └─ www/
│  └─ systemd/
│     ├─ song-blog-ingest.service
│     ├─ song-blog-ingest.timer
│     ├─ song-blog-backup.service
│     └─ song-blog-backup.timer
├─ scripts/
│  └─ backup.sh
├─ data/
│  ├─ static/
│  └─ media/
└─ backups/
```

必须把这些内容加入 `.gitignore`：

```gitignore
.env
backups/
data/media/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
```

`data/static/` 可以不提交，生产环境通过 `collectstatic` 生成。

---

## 4. Python 依赖

`requirements.txt` 至少包含：

```text
Django>=5.2,<5.3
gunicorn>=23,<24
mysqlclient>=2.2,<3
Pillow>=11,<13
httpx>=0.28,<1
feedparser>=6,<7
```

说明：

- Django 官方推荐使用原生驱动 `mysqlclient`。
- `Pillow` 用于头像、封面等图片字段；项目没有图片字段时可删除。
- `httpx`、`feedparser` 用于采集 API 和 RSS；如果代码没有使用可删除。
- 锁文件或经过测试的精确版本应提交 Git。上线更新依赖前先在本机测试。

---

## 5. Django 的 MySQL 与生产配置

在 `config/settings.py` 中从环境变量读取配置。不要把密码或 API Key 写进源码。

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {
        "1", "true", "yes", "on"
    }


def env_list(name: str) -> list[str]:
    return [
        item.strip()
        for item in os.getenv(name, "").split(",")
        if item.strip()
    ]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ["MYSQL_DATABASE"],
        "USER": os.environ["MYSQL_USER"],
        "PASSWORD": os.environ["MYSQL_PASSWORD"],
        "HOST": os.getenv("MYSQL_HOST", "db"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "isolation_level": "read committed",
            "connect_timeout": 10,
        },
        # 测试永远使用独立数据库，防止误碰正式数据。
        "TEST": {
            "NAME": os.getenv("MYSQL_TEST_DATABASE", "song_blog_test"),
        },
    }
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Nginx 会把原始 HTTPS 协议传给 Django。
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)

# HTTPS 稳定运行后再逐步开启 HSTS。第一次不要直接设一年。
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

关键点：

- 容器之间用服务名通信，因此数据库主机名是 `db`，不是 `localhost`。
- 必须使用 `utf8mb4`，否则 emoji 和部分 Unicode 字符无法正确保存。
- 使用 InnoDB，以获得事务和外键支持。
- Django 对 MySQL 默认使用 `read committed`，不要随意改回 `repeatable read`。
- MySQL 8.4 默认启用严格模式；Compose 中也会显式配置，避免字段截断时只产生警告而丢失数据。
- MySQL 8.4 默认使用 `caching_sha2_password`；保持 `mysqlclient` 为较新版本即可，不要照搬旧教程重新启用已经弃用的 `mysql_native_password`。
- 默认排序规则 `utf8mb4_0900_ai_ci` 不区分大小写。若某个唯一字段必须区分大小写，应为该字段单独设置合适的 collation，而不是全库盲目修改。

### 5.1 健康检查端点

在 `config/urls.py` 中增加存活与就绪检查。生产健康检查不要输出密钥、版本或异常堆栈。

```python
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import path


def health_live(request):
    return JsonResponse({"status": "ok"})


def health_ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/live", health_live),
    path("health/ready", health_ready),
    path("admin/", admin.site.urls),
]
```

可再用 Nginx 对 `/health/` 做访问限制，但不要删除外部可用性监测所需的端点。

---

## 6. 环境变量

创建 `.env.example` 并提交 Git：

```dotenv
# Django
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,blog.example.com,www.blog.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://blog.example.com,https://www.blog.example.com
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SECURE_COOKIES=False
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False

# MySQL；MYSQL_USER 不得填写 root
MYSQL_DATABASE=song_blog
MYSQL_TEST_DATABASE=song_blog_test
MYSQL_USER=song_blog_app
MYSQL_PASSWORD=replace-with-a-long-random-password
MYSQL_ROOT_PASSWORD=replace-with-another-long-random-password
MYSQL_HOST=db
MYSQL_PORT=3306

# Nginx 在首次签发证书前使用 HTTP 配置
NGINX_CONF=./deploy/nginx/http.conf

# 数据采集；没有使用的项留空
GITHUB_TOKEN=
HUGGINGFACE_TOKEN=
LLM_API_KEY=
LLM_BASE_URL=
```

本机复制一份：

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

把生成的不同随机值分别填入 `DJANGO_SECRET_KEY`、`MYSQL_PASSWORD` 和 `MYSQL_ROOT_PASSWORD`。服务器上还应限制文件权限：

```bash
chmod 600 .env
```

注意：

- `.env` 永远不要提交 Git、发到群聊或截图公开。
- 前端 JavaScript 中不得出现数据库密码或 AI API Key。
- `MYSQL_ROOT_PASSWORD` 仅用于数据库初始化和维护，Django 使用非 root 的 `MYSQL_USER`。
- MySQL 官方镜像只会在空数据目录第一次启动时使用这些初始化变量。数据库已经创建后，修改 `.env` 不会自动修改库内账号密码。

---

## 7. Docker 镜像

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       default-libmysqlclient-dev \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

如果 Django 项目包不是 `config`，修改 `config.wsgi:application`。

创建 `.dockerignore`：

```dockerignore
.git
.gitignore
.env
.venv
venv
__pycache__
*.py[cod]
.pytest_cache
.coverage
backups
data
*.sqlite3
```

正式项目建议在测试通过后把基础镜像和 Python 依赖锁定到经过验证的版本，并定期主动升级安全补丁，不要长期依赖 `latest`。

---

## 8. Docker Compose

### 8.1 基础服务

创建 `compose.yaml`：

```yaml
name: song-blog

services:
  db:
    image: mysql:8.4
    restart: unless-stopped
    env_file:
      - .env
    environment:
      TZ: Asia/Shanghai
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_0900_ai_ci
      - --default-storage-engine=InnoDB
      - --default-time-zone=+00:00
      - --sql-mode=ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - backend
    healthcheck:
      test:
        - CMD-SHELL
        - >-
          MYSQL_PWD="$$MYSQL_PASSWORD" mysql -h 127.0.0.1
          -u"$$MYSQL_USER" -D "$$MYSQL_DATABASE"
          -e 'SELECT 1' >/dev/null 2>&1
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 40s
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"

  web:
    build:
      context: .
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    ports:
      - 127.0.0.1:8000:8000
    volumes:
      - ./data/static:/app/staticfiles
      - ./data/media:/app/media
    networks:
      - backend
      - frontend
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - >-
          import urllib.request;
          urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"

volumes:
  mysql_data:

networks:
  backend:
    internal: true
  frontend:
```

这里故意没有为 `db` 配置 `ports`，所以 MySQL 不会暴露到宿主机或公网。需要执行 SQL 时使用：

```bash
docker compose exec db mysql -u root -p
```

### 8.2 生产 Nginx

创建 `compose.prod.yaml`：

```yaml
services:
  nginx:
    image: nginx:1.28-alpine
    restart: unless-stopped
    depends_on:
      web:
        condition: service_healthy
    ports:
      - 80:80
      - 443:443
    volumes:
      - ${NGINX_CONF:-./deploy/nginx/http.conf}:/etc/nginx/conf.d/default.conf:ro
      - ./data/static:/srv/static:ro
      - ./data/media:/srv/media:ro
      - ./deploy/certbot/www:/var/www/certbot:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    networks:
      - frontend
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"
```

本机开发只运行 `compose.yaml`；服务器使用两个文件：

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

---

## 9. Nginx 配置

### 9.1 首次签发证书前的 HTTP 配置

创建 `deploy/nginx/http.conf`，将域名替换为你的域名：

```nginx
upstream django_app {
    server web:8000;
}

server {
    listen 80;
    server_name blog.example.com www.blog.example.com;

    client_max_body_size 10m;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias /srv/static/;
        access_log off;
        expires 7d;
    }

    location /media/ {
        alias /srv/media/;
        add_header X-Content-Type-Options nosniff always;
    }

    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }
}
```

### 9.2 HTTPS 配置

证书签发成功后使用 `deploy/nginx/https.conf`：

```nginx
upstream django_app {
    server web:8000;
}

server {
    listen 80;
    server_name blog.example.com www.blog.example.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name blog.example.com www.blog.example.com;

    ssl_certificate /etc/letsencrypt/live/blog.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blog.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    client_max_body_size 10m;

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /static/ {
        alias /srv/static/;
        access_log off;
        expires 7d;
    }

    location /media/ {
        alias /srv/media/;
        add_header X-Content-Type-Options nosniff always;
    }

    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }
}
```

若只使用一个域名，删除另一个 `server_name` 和申请证书时对应的 `-d` 参数。

---

## 10. Windows 本机启动

### 10.1 准备

1. 安装 Git。
2. 安装 Docker Desktop，并启用 WSL 2 后端。
3. 在项目根目录复制 `.env.example` 为 `.env`，填入随机密钥。
4. 本机 `.env` 可暂时使用：

```dotenv
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SECURE_COOKIES=False
```

### 10.2 构建和初始化

```powershell
docker compose config
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

打开 `http://127.0.0.1:8000`。

第一次运行测试前，为测试创建独立数据库。下面的名称要与 `.env` 一致：

```powershell
docker compose exec db mysql -u root -p
```

在 MySQL 提示符中输入：

```sql
CREATE DATABASE IF NOT EXISTS song_blog_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON song_blog_test.* TO 'song_blog_app'@'%';
FLUSH PRIVILEGES;
EXIT;
```

测试会创建和销毁测试表，只使用 `song_blog_test`，不会访问 `song_blog`。生产服务器不需要创建测试数据库，测试应在本机或 CI 先通过。

### 10.3 常用命令

```powershell
# 查看状态
docker compose ps

# 查看 Django 和 MySQL 日志
docker compose logs --tail 200 web db

# 执行测试
docker compose run --rm web python manage.py test

# 运行 Django 系统检查
docker compose run --rm web python manage.py check

# 停止服务但保留数据库
docker compose down
```

不要运行：

```text
docker compose down -v
```

`-v` 会删除 MySQL 命名卷，可能导致数据库数据不可恢复。

---

## 11. Ubuntu 服务器初始化

### 11.1 域名解析和端口

在域名 DNS 控制台添加：

| 记录 | 类型 | 值 |
|---|---|---|
| `@` 或 `blog` | A | 服务器公网 IPv4 |
| `www` | A | 服务器公网 IPv4；不使用可省略 |

云安全组和 UFW 都应使用最小开放规则：

| 端口 | 是否公网开放 | 用途 |
|---|---|---|
| `22/TCP` | 仅自己的固定 IP；必要时临时放开 | SSH |
| `80/TCP` | 是 | HTTP 跳转、证书验证 |
| `443/TCP` | 是 | HTTPS |
| `8000/TCP` | 否 | Gunicorn，仅宿主机回环/容器网络 |
| `3306/TCP` | 否 | MySQL，仅 Compose 内部网络 |

在确认 SSH 规则不会把自己锁在服务器外后执行：

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl ca-certificates ufw snapd

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

### 11.2 安装 Docker Engine 与 Compose 插件

按 Docker 官方 Ubuntu 仓库安装：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"${UBUNTU_CODENAME:-$VERSION_CODENAME}\") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

sudo usermod -aG docker "$USER"
```

退出 SSH 后重新登录，让 Docker 用户组生效。验证：

```bash
docker --version
docker compose version
```

Docker 发布容器端口时可能绕过部分 UFW 规则，因此仍需同时正确配置云安全组，并且不要在 Compose 中发布 `3306`。

### 11.3 拉取代码

```bash
sudo mkdir -p /opt/song-blog
sudo chown "$USER":"$USER" /opt/song-blog
git clone https://github.com/songshihua/<repository-name>.git /opt/song-blog
cd /opt/song-blog

cp .env.example .env
chmod 600 .env
mkdir -p data/static data/media backups deploy/certbot/www
sudo chown -R 10001:10001 data/static data/media
chmod 755 data data/static data/media
```

编辑 `.env`，至少保证：

```dotenv
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=blog.example.com,www.blog.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://blog.example.com,https://www.blog.example.com
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_SECURE_COOKIES=False
DJANGO_SECURE_HSTS_SECONDS=0
NGINX_CONF=./deploy/nginx/http.conf
```

首次签发证书前保持安全跳转和安全 Cookie 为 `False`，否则 HTTP 验证和后台登录可能形成错误跳转。

---

## 12. 第一次发布

在 `/opt/song-blog` 执行：

```bash
docker compose -f compose.yaml -f compose.prod.yaml config
docker compose -f compose.yaml -f compose.prod.yaml build web
docker compose -f compose.yaml -f compose.prod.yaml up -d db

docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py migrate
docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py collectstatic --noinput
docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py createsuperuser

docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose -f compose.yaml -f compose.prod.yaml ps
```

验证：

```bash
curl -I http://127.0.0.1:8000/health/live
curl -I http://blog.example.com/health/ready
docker compose -f compose.yaml -f compose.prod.yaml logs --tail 200 web db nginx
```

核对数据库实际配置：

```bash
docker compose -f compose.yaml -f compose.prod.yaml exec -T db \
  sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" \
  -e "SELECT VERSION(); SELECT @@character_set_server, @@collation_server, @@sql_mode, @@default_storage_engine, @@transaction_isolation;"'
```

迁移和 `collectstatic` 使用一次性命令执行，不要把 `migrate` 塞进每个 Gunicorn 容器的启动命令。否则将来扩容 Web 实例时，多个实例可能同时迁移数据库。

---

## 13. 配置 HTTPS

### 13.1 安装 Certbot

```bash
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/local/bin/certbot
```

若软链接已存在，不要重复创建。

### 13.2 签发证书

先确认域名已解析到当前服务器，并且 HTTP 页面可以访问：

```bash
sudo certbot certonly \
  --webroot \
  -w /opt/song-blog/deploy/certbot/www \
  -d blog.example.com \
  -d www.blog.example.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email
```

签发成功后修改 `.env`：

```dotenv
NGINX_CONF=./deploy/nginx/https.conf
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_COOKIES=True
```

重建相关容器：

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d \
  --force-recreate web nginx
```

验证：

```bash
curl -I https://blog.example.com/health/ready
sudo certbot renew --dry-run
```

确认 HTTPS 和所有子域名均正确运行一段时间后，可以逐步设置：

```dotenv
DJANGO_SECURE_HSTS_SECONDS=3600
```

先观察，再增加到更长时间。只有确定所有子域名永久支持 HTTPS 时，才考虑开启 `HSTS_INCLUDE_SUBDOMAINS`；不要一开始就启用 preload。

### 13.3 证书续期后重载 Nginx

Certbot 通常会安装自动续期 timer。创建部署钩子 `/etc/letsencrypt/renewal-hooks/deploy/reload-song-blog-nginx.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /opt/song-blog
/usr/bin/docker compose -f compose.yaml -f compose.prod.yaml \
  exec -T nginx nginx -s reload
```

然后：

```bash
sudo chmod 750 /etc/letsencrypt/renewal-hooks/deploy/reload-song-blog-nginx.sh
sudo certbot renew --dry-run
```

---

## 14. 每日 AI 内容采集

假设采集命令为：

```bash
python manage.py ingest_sources
```

命令应满足：

- 幂等：同一篇论文或文章重复采集不会重复插入。
- 具有唯一键，例如 `source + external_id` 或规范化 URL 的唯一约束。
- 对每个外部 API 设置连接超时、读取超时、有限重试和指数退避。
- 遵守 arXiv、GitHub 等来源的速率限制和使用条款。
- 记录任务开始、结束、状态、新增数量和错误摘要。
- 使用数据库级锁阻止两个采集任务同时运行。

MySQL 锁的核心写法可放在 management command 中：

```python
from contextlib import contextmanager
from django.db import connection


@contextmanager
def mysql_named_lock(name: str):
    with connection.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [name])
        acquired = cursor.fetchone()[0] == 1
    if not acquired:
        raise RuntimeError(f"task already running: {name}")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [name])
```

在命令主逻辑外包裹：

```python
with mysql_named_lock("song_blog_ingest_sources"):
    run_ingestion()
```

### 14.1 systemd service

创建 `/etc/systemd/system/song-blog-ingest.service`：

```ini
[Unit]
Description=Song Blog AI source ingestion
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/song-blog
ExecStart=/usr/bin/docker compose -f compose.yaml -f compose.prod.yaml run --rm web python manage.py ingest_sources
TimeoutStartSec=45min
```

### 14.2 systemd timer

创建 `/etc/systemd/system/song-blog-ingest.timer`：

```ini
[Unit]
Description=Run Song Blog ingestion every morning

[Timer]
OnCalendar=*-*-* 08:00:00 Asia/Shanghai
RandomizedDelaySec=10min
Persistent=true
Unit=song-blog-ingest.service

[Install]
WantedBy=timers.target
```

启用并手动测试：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now song-blog-ingest.timer
sudo systemctl start song-blog-ingest.service
systemctl list-timers song-blog-ingest.timer
journalctl -u song-blog-ingest.service -n 100 --no-pager
```

如果一次任务可能超过 24 小时，应定义“跳过、排队或合并”策略，不能让任务无限并发。

---

## 15. MySQL 与媒体文件备份

### 15.1 备份目标

建议第一版定义：

- RPO：最多丢失 24 小时数据。
- RTO：4 小时内恢复网站。
- 每日备份保留 14 天；重要节点另外保留手工备份。
- 数据库和 `data/media` 都要备份。
- 至少再复制一份到服务器之外。同一台 VPS、同一块系统盘上的备份不算异地备份。

### 15.2 备份脚本

创建 `scripts/backup.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

project_dir=/opt/song-blog
backup_dir=/opt/song-blog/backups
timestamp=$(date -u +%Y%m%dT%H%M%SZ)

cd "$project_dir"
mkdir -p "$backup_dir"

db_file="$backup_dir/mysql_${timestamp}.sql.gz"
media_file="$backup_dir/media_${timestamp}.tar.gz"

/usr/bin/docker compose -f compose.yaml -f compose.prod.yaml exec -T db \
  sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump \
    -h 127.0.0.1 \
    -u"$MYSQL_USER" \
    --single-transaction \
    --quick \
    --routines \
    --events \
    --triggers \
    --no-tablespaces \
    "$MYSQL_DATABASE"' \
  | gzip -9 > "$db_file"

tar -C "$project_dir/data" -czf "$media_file" media

test -s "$db_file"
test -s "$media_file"
sha256sum "$db_file" "$media_file" > "$backup_dir/checksums_${timestamp}.sha256"

# 只清理本项目 backups 目录中超过 14 天的自动备份。
find "$backup_dir" -maxdepth 1 -type f -mtime +14 \
  \( -name 'mysql_*.sql.gz' -o -name 'media_*.tar.gz' -o -name 'checksums_*.sha256' \) \
  -delete
```

给脚本执行权限并手工测试：

```bash
chmod 750 scripts/backup.sh
./scripts/backup.sh
ls -lh backups/
sha256sum -c backups/checksums_<timestamp>.sha256
```

生产环境可用 `rclone` 或云厂商 CLI，把新备份同步到对象存储。对象存储凭证应使用最小权限，只允许访问指定备份桶。

### 15.3 定时备份

创建 `/etc/systemd/system/song-blog-backup.service`：

```ini
[Unit]
Description=Backup Song Blog MySQL and media files
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/song-blog
ExecStart=/opt/song-blog/scripts/backup.sh
```

创建 `/etc/systemd/system/song-blog-backup.timer`：

```ini
[Unit]
Description=Run Song Blog backup every night

[Timer]
OnCalendar=*-*-* 03:30:00 Asia/Shanghai
Persistent=true
Unit=song-blog-backup.service

[Install]
WantedBy=timers.target
```

启用并测试：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now song-blog-backup.timer
sudo systemctl start song-blog-backup.service
journalctl -u song-blog-backup.service -n 100 --no-pager
```

### 15.4 恢复演练

恢复不能只看“备份文件存在”。至少每月向全新的测试数据库卷做一次恢复演练，不要覆盖生产卷。

一个安全的演练流程是：

1. 把备份下载到隔离的测试环境。
2. 启动一个空的 MySQL 8.4 实例。
3. 解压并导入 SQL。
4. 恢复媒体文件。
5. 使用测试配置启动 Django。
6. 检查文章数量、项目、标签关系、后台登录、图片和最新采集记录。
7. 记录恢复耗时及错误。

逻辑导入的核心命令为：

```bash
gzip -dc mysql_<timestamp>.sql.gz \
  | docker compose exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"'
```

该命令会写入目标数据库。只可对确认过的空测试库或明确要恢复的目标库执行，禁止直接拿生产库做演练。

---

## 16. 日常发布更新

每次发布前先确认 Git 状态、测试和备份：

```bash
cd /opt/song-blog
git status
./scripts/backup.sh
git pull --ff-only

docker compose -f compose.yaml -f compose.prod.yaml build web
docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py migrate --plan
docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py migrate
docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py collectstatic --noinput
docker compose -f compose.yaml -f compose.prod.yaml up -d --remove-orphans
```

这里默认测试已经在本机或 CI 的独立 MySQL 测试库中通过，不要把生产服务器当测试环境。

发布后检查：

```bash
docker compose -f compose.yaml -f compose.prod.yaml ps
docker compose -f compose.yaml -f compose.prod.yaml logs --tail 200 web nginx db
docker compose -f compose.yaml -f compose.prod.yaml exec -T web \
  python manage.py check --deploy
curl -I https://blog.example.com/health/ready
```

数据库迁移可能不可逆。涉及删除字段、改数据或大表结构变化时，先做经过验证的备份，并使用“先兼容、再迁移、最后清理旧字段”的多阶段发布方式。

---

## 17. 日志、监控和安全

### 17.1 最低监控项

- 从服务器外部每 5 分钟访问正式域名和 `/health/ready`。
- 监控 HTTPS 证书剩余有效期。
- 监控磁盘、内存、负载和容器重启次数。
- 监控每日采集与备份任务是否成功。
- 监控备份文件是否为空、体积是否异常、异地同步是否成功。

常用查看命令：

```bash
docker compose -f compose.yaml -f compose.prod.yaml ps
docker compose -f compose.yaml -f compose.prod.yaml stats
docker compose -f compose.yaml -f compose.prod.yaml logs -f --tail 200 web
df -h
free -h
systemctl list-timers --all
```

### 17.2 上线安全清单

- [ ] `DEBUG=False`。
- [ ] `ALLOWED_HOSTS` 只有真实域名。
- [ ] `CSRF_TRUSTED_ORIGINS` 使用完整的 `https://` 地址。
- [ ] `SECRET_KEY`、MySQL 密码和 API Key 未进入 Git。
- [ ] MySQL 使用非 root 应用账号。
- [ ] 云安全组和 UFW 都未开放 `3306`、`8000`。
- [ ] 网站使用 HTTPS，安全 Cookie 已开启。
- [ ] 已运行 `python manage.py check --deploy`。
- [ ] Django Admin 使用独立强密码；可以再加双因素认证或入口保护。
- [ ] 用户上传文件视为不可信内容，不允许当脚本执行。
- [ ] 容器日志已轮转，不会无限占满磁盘。
- [ ] Ubuntu 自动安全更新已启用并定期检查。
- [ ] 每日数据库与媒体备份已自动运行，并至少有一份在服务器外。
- [ ] 已真实完成一次从空环境恢复的演练。

---

## 18. 常见故障

### 18.1 `Can't connect to MySQL server`

检查：

```bash
docker compose ps
docker compose logs --tail 200 db web
docker compose exec web python -c \
  "import socket; print(socket.gethostbyname('db'))"
```

常见原因：

- `MYSQL_HOST` 错写为 `localhost`；容器中应为 `db`。
- MySQL 尚未通过健康检查。
- `.env` 中数据库名、用户或密码不一致。

### 18.2 修改 `.env` 后仍提示 Access denied

MySQL 数据卷已经初始化后，修改 `MYSQL_USER` 或密码不会自动修改库内账号。应登录 MySQL 后明确执行账号修改，例如：

```sql
ALTER USER 'song_blog_app'@'%' IDENTIFIED BY 'new-long-random-password';
FLUSH PRIVILEGES;
```

再同步修改 `.env` 并重建 Web 容器。只有在明确不需要任何现有数据时，才可以删除数据库卷重新初始化。

### 18.3 中文或 emoji 保存失败

检查：

```sql
SHOW VARIABLES LIKE 'character_set_server';
SHOW VARIABLES LIKE 'collation_server';
SHOW CREATE DATABASE song_blog;
```

期望字符集为 `utf8mb4`。旧表若不是 `utf8mb4`，需要先备份，再制定独立的数据迁移方案。

### 18.4 Nginx 返回 502

```bash
docker compose -f compose.yaml -f compose.prod.yaml ps
docker compose -f compose.yaml -f compose.prod.yaml logs --tail 200 web nginx
curl -I http://127.0.0.1:8000/health/live
```

常见原因是 Gunicorn 未启动、`config.wsgi` 写错、迁移失败或静态/媒体目录权限错误。

### 18.5 后台登录出现 CSRF 403

确认：

- `DJANGO_CSRF_TRUSTED_ORIGINS` 包含 `https://正式域名`。
- Nginx 设置了 `X-Forwarded-Proto $scheme`。
- Django 设置了 `SECURE_PROXY_SSL_HEADER`。
- 浏览器访问的域名与配置一致，不要混用 IP、根域名和 `www`。

### 18.6 静态文件 404

```bash
docker compose -f compose.yaml -f compose.prod.yaml run --rm web \
  python manage.py collectstatic --noinput
ls -la data/static | head
docker compose -f compose.yaml -f compose.prod.yaml restart nginx
```

---

## 19. 正式交付前验收

### 页面与招聘展示

- [ ] 首页 3 秒内能看清姓名、学校、研究方向和求职目标。
- [ ] GitHub 链接指向 `https://github.com/songshihua/`。
- [ ] 项目页写清问题、你的贡献、结果和可验证链接。
- [ ] 博客文章有发布日期、标签、目录和代码高亮。
- [ ] AI 前沿页明确标注来源、发布时间、原文链接和更新时间。
- [ ] 手机端、Chrome、Edge 均检查过。
- [ ] 示例数据已替换，未把虚构指标当作真实成果。

### 技术与运维

- [ ] `docker compose ps` 中服务正常。
- [ ] `/health/live` 和 `/health/ready` 返回 200。
- [ ] HTTPS、HTTP 跳转和证书自动续期测试通过。
- [ ] `python manage.py check --deploy` 无关键告警。
- [ ] MySQL 没有公网端口。
- [ ] 每日采集任务不会重复插入或并发执行。
- [ ] 每日备份成功、已异地保存、已完成恢复演练。
- [ ] 重启服务器后 Docker 服务和容器会自动恢复。
- [ ] 国内服务器的网站底部已展示正确备案号。

---

## 20. 官方参考资料

- [Django 5.2：MySQL 数据库说明](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes)
- [Django 5.2：部署检查表](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django：使用 Gunicorn 部署 WSGI](https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/)
- [MySQL 8.4：备份与恢复](https://dev.mysql.com/doc/refman/8.4/en/backup-and-recovery.html)
- [MySQL Docker 官方镜像](https://hub.docker.com/_/mysql)
- [Docker：Ubuntu 安装说明](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose：按健康状态控制启动顺序](https://docs.docker.com/compose/how-tos/startup-order/)
- [Certbot：Nginx/Ubuntu HTTPS 指南](https://certbot.eff.org/instructions)
- [Ubuntu：UFW 防火墙](https://documentation.ubuntu.com/server/how-to/security/firewalls/)
- [工信部：非经营性互联网信息服务备案管理办法](https://www.miit.gov.cn/gyhxxhb/jgsj/cyzcyfgs/bmgz/xxtxl/art/2024/art_84a0cfa0ebd049bbbe751dca9a008e56.html)

---

## 21. 推荐实施顺序

如果目前项目还没有开始编码，按下面顺序推进最省事：

1. 在 Windows 安装 Git 和 Docker Desktop。
2. 创建 Django 项目和 `portfolio`、`blog`、`radar` 三个应用。
3. 直接接入本地 MySQL 8.4 容器，完成模型和后台管理。
4. 实现首页、项目页、文章页，再实现 AI 前沿列表和搜索。
5. 把各数据源采集写成幂等的 `ingest_sources` management command。
6. 补测试、健康检查、Dockerfile 和 Compose。
7. 本机完成一次“删除测试环境后重建”的演练。
8. 购买服务器和域名；使用内地服务器时同步办理备案。
9. 按本文执行首次发布、HTTPS、定时采集和异地备份。
10. 在把网址放进简历之前，请朋友用手机和校外网络完整检查一次。

第一版的完成标准不是功能最多，而是：页面稳定、内容真实、访问快速、来源可追溯、数据可恢复。
