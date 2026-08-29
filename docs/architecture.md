# 架构说明

```text
Browser
  ├─ React/Vinext frontend :3000
  └─ /api/v1, /admin, /health
            │
            ▼
       Django/DRF :8000
            │
            ▼
        MySQL 8.4
```

## 边界

- `frontend/` 只负责公开展示、筛选和设备本地交互，不持有服务端密钥。
- `backend/` 负责模型、校验、只读 API、Admin、健康检查和一次性采集任务。
- `apps/core` 管理个人档案与共享主题；`portfolio` 管理项目；`blog` 管理文章；`radar` 管理来源、条目和采集记录。
- 写操作只通过 Django Admin 和受控 management command 完成。
- 第一阶段没有公众账户、评论、Redis、Celery 或搜索集群。

## 环境

- `config.settings.development`：本机 API 与 CORS。
- `config.settings.test`：独立 MySQL 测试库。
- `config.settings.production`：强制显式密钥与域名，并由 Nginx 终止 TLS。

## 数据真实性

`seed_demo` 只创建带 `is_demo=true` 的幂等样例。性能曲线、趋势、论文和同步状态在接入可验证来源之前不得改成真实口吻。
