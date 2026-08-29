# Contributing

1. 从 `main` 创建短生命周期分支。
2. 不提交 `.env`、Token、数据库卷、媒体文件或备份。
3. 业务模型变更必须提交迁移，并执行 `makemigrations --check --dry-run`。
4. 公开 API 默认只读；新增写接口必须说明身份认证、授权和 CSRF 策略。
5. 新增演示内容必须带 `is_demo=true`，界面必须显示 `SAMPLE / DEMO`。
6. 提交前运行 `scripts/check.ps1`，确保后端检查、测试、前端类型检查与构建通过。
7. 注释说明约束和设计原因，不逐行复述代码。

建议使用 Conventional Commits，例如 `feat(radar): add source filter`、`fix(api): hide future articles`。
