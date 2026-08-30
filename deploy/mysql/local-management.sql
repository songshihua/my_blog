-- SS·LAB 本地 MySQL 管理查询
--
-- 安全约定：
-- 1. 本文件不保存账号、密码或 Token。
-- 2. 默认部分只包含只读查询，并显式开启 READ ONLY 事务。
-- 3. 请先连接到 MYSQL_DATABASE 指定的数据库（默认 song_blog）再执行。
-- 4. Django migrations 是数据库结构的唯一事实来源；不要手工修改表结构。
-- 5. 文件末尾的维护示例全部处于注释状态。执行任何写操作前必须先备份。

SET NAMES utf8mb4;
SET time_zone = '+00:00';
START TRANSACTION READ ONLY;

-- ---------------------------------------------------------------------
-- 1. 当前连接与服务端配置
-- ---------------------------------------------------------------------

SELECT
    DATABASE() AS database_name,
    CURRENT_USER() AS authenticated_account,
    VERSION() AS mysql_version,
    @@character_set_server AS server_character_set,
    @@collation_server AS server_collation,
    @@time_zone AS session_time_zone,
    @@sql_mode AS sql_mode;

SHOW TABLES;

-- ---------------------------------------------------------------------
-- 2. 表规模与存储引擎
-- TABLE_ROWS 对 InnoDB 是估算值；精确业务数量见后续 COUNT 查询。
-- ---------------------------------------------------------------------

SELECT
    TABLE_NAME AS table_name,
    ENGINE AS storage_engine,
    TABLE_COLLATION AS table_collation,
    TABLE_ROWS AS estimated_rows,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_mb,
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS index_mb,
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS total_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC, TABLE_NAME;

-- ---------------------------------------------------------------------
-- 3. Django 迁移与核心业务总量
-- ---------------------------------------------------------------------

SELECT
    app,
    COUNT(*) AS migration_count,
    MAX(applied) AS latest_applied_at
FROM django_migrations
GROUP BY app
ORDER BY app;

SELECT
    (SELECT COUNT(*) FROM auth_user) AS user_count,
    (SELECT COUNT(*) FROM core_siteprofile) AS profile_count,
    (SELECT COUNT(*) FROM core_topic) AS topic_count,
    (SELECT COUNT(*) FROM blog_category) AS article_category_count,
    (SELECT COUNT(*) FROM blog_article) AS article_count,
    (SELECT COUNT(*) FROM blog_articlesourcefile) AS imported_note_file_count,
    (SELECT COUNT(*) FROM portfolio_project) AS project_count,
    (SELECT COUNT(*) FROM radar_radarsource) AS radar_source_count,
    (SELECT COUNT(*) FROM radar_radaritem) AS radar_item_count,
    (SELECT COUNT(*) FROM radar_ingestionrun) AS ingestion_run_count;

-- ---------------------------------------------------------------------
-- 4. 文章与项目内容状态
-- ---------------------------------------------------------------------

SELECT
    category.id,
    category.name,
    category.slug,
    parent.slug AS parent_slug,
    category.sort_order,
    COUNT(article.id) AS direct_article_count
FROM blog_category AS category
LEFT JOIN blog_category AS parent ON parent.id = category.parent_id
LEFT JOIN blog_article AS article ON article.category_id = category.id
GROUP BY category.id, category.name, category.slug, parent.slug, category.sort_order
ORDER BY category.sort_order, category.name;

SELECT
    status,
    is_demo,
    COUNT(*) AS item_count,
    MAX(updated_at) AS latest_updated_at
FROM blog_article
GROUP BY status, is_demo
ORDER BY status, is_demo;

SELECT
    source.id,
    article.title,
    source.original_filename,
    source.source_format,
    source.size_bytes,
    source.extracted_at,
    article.updated_at
FROM blog_articlesourcefile AS source
INNER JOIN blog_article AS article ON article.id = source.article_id
ORDER BY source.extracted_at DESC
LIMIT 30;

SELECT
    external_source,
    category,
    is_published,
    is_demo,
    COUNT(*) AS item_count,
    MAX(last_synced_at) AS latest_synced_at,
    MAX(updated_at) AS latest_updated_at
FROM portfolio_project
GROUP BY external_source, category, is_published, is_demo
ORDER BY external_source, category, is_published DESC, is_demo;

SELECT
    id,
    title,
    slug,
    external_source,
    is_published,
    is_demo,
    last_synced_at,
    updated_at
FROM portfolio_project
ORDER BY updated_at DESC
LIMIT 20;

-- ---------------------------------------------------------------------
-- 5. AI 雷达来源健康度、同步记录与内容分布
-- 时间字段以 UTC 保存；TIMESTAMPDIFF 结果用于快速判断数据新鲜度。
-- ---------------------------------------------------------------------

SELECT
    id,
    name,
    source_type,
    is_enabled,
    status,
    last_item_count,
    last_attempt_at,
    last_success_at,
    TIMESTAMPDIFF(MINUTE, last_success_at, UTC_TIMESTAMP()) AS minutes_since_success,
    last_error_at,
    LEFT(last_error_summary, 200) AS last_error_summary
FROM radar_radarsource
ORDER BY name;

SELECT
    run.id,
    source.source_type,
    run.status,
    run.started_at,
    run.finished_at,
    TIMESTAMPDIFF(SECOND, run.started_at, run.finished_at) AS duration_seconds,
    run.inserted_count,
    run.updated_count,
    run.skipped_count,
    run.error_count,
    LEFT(run.error_summary, 200) AS error_summary
FROM radar_ingestionrun AS run
LEFT JOIN radar_radarsource AS source ON source.id = run.source_id
ORDER BY run.started_at DESC
LIMIT 30;

SELECT
    source.source_type,
    item.kind,
    item.is_visible,
    item.is_demo,
    COUNT(*) AS item_count,
    MAX(item.published_at) AS newest_published_at,
    MAX(item.fetched_at) AS latest_fetched_at
FROM radar_radaritem AS item
INNER JOIN radar_radarsource AS source ON source.id = item.source_id
GROUP BY source.source_type, item.kind, item.is_visible, item.is_demo
ORDER BY source.source_type, item.kind, item.is_visible DESC, item.is_demo;

SELECT
    item.id,
    source.source_type,
    item.kind,
    item.title,
    item.published_at,
    item.fetched_at,
    item.is_visible,
    item.is_demo
FROM radar_radaritem AS item
INNER JOIN radar_radarsource AS source ON source.id = item.source_id
ORDER BY item.fetched_at DESC
LIMIT 30;

-- ---------------------------------------------------------------------
-- 6. 管理员账号状态（刻意不查询 password 字段）
-- ---------------------------------------------------------------------

SELECT
    id,
    username,
    email,
    is_staff,
    is_superuser,
    is_active,
    last_login,
    date_joined
FROM auth_user
ORDER BY id;

-- ---------------------------------------------------------------------
-- 7. 索引检查：便于确认迁移创建的索引已存在
-- ---------------------------------------------------------------------

SELECT
    TABLE_NAME AS table_name,
    INDEX_NAME AS index_name,
    NON_UNIQUE AS is_non_unique,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS columns_in_order
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE
ORDER BY TABLE_NAME, INDEX_NAME;

COMMIT;

-- =====================================================================
-- 可选维护示例（默认禁用）
-- =====================================================================
-- 以下语句全部保持注释，不能直接执行。写操作前应先：
-- 1. 使用 scripts/export-database-schema.ps1 导出结构，并另做完整数据备份；
-- 2. 在测试库 song_blog_test 验证 WHERE 条件；
-- 3. 使用事务先 SELECT、再 DELETE，核对 ROW_COUNT() 后优先 ROLLBACK；
-- 4. 确认无误时才将 ROLLBACK 改为 COMMIT。
--
-- 注意：ALTER、DROP、TRUNCATE 等 DDL 会隐式提交，不能依赖 ROLLBACK 恢复，
-- 因此本文件不提供这类示例。数据库结构必须通过 Django migration 修改。
--
-- 示例：清理已确认不再需要的演示雷达条目。
-- START TRANSACTION;
-- SELECT id, title, source_id, fetched_at
-- FROM radar_radaritem
-- WHERE is_demo = 1
-- ORDER BY id
-- FOR UPDATE;
-- DELETE FROM radar_radaritem WHERE is_demo = 1;
-- SELECT ROW_COUNT() AS affected_rows;
-- ROLLBACK;
