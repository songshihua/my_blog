from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, Topic


class RadarSource(TimeStampedModel):
    class SourceType(models.TextChoices):
        ARXIV = "arxiv", "arXiv"
        GITHUB = "github", "GitHub"
        HUGGINGFACE = "huggingface", "Hugging Face"
        OPENREVIEW = "openreview", "OpenReview"

    class Status(models.TextChoices):
        DISABLED = "disabled", "未启用"
        IDLE = "idle", "待同步"
        RUNNING = "running", "同步中"
        SUCCESS = "success", "正常"
        ERROR = "error", "异常"

    name = models.CharField("名称", max_length=80)
    source_type = models.CharField(
        "来源类型", max_length=24, choices=SourceType.choices, unique=True
    )
    homepage_url = models.URLField("主页")
    is_enabled = models.BooleanField("启用", default=False)
    status = models.CharField(
        "状态", max_length=16, choices=Status.choices, default=Status.DISABLED
    )
    last_success_at = models.DateTimeField("最后成功时间", blank=True, null=True)
    last_error_at = models.DateTimeField("最后失败时间", blank=True, null=True)
    last_error_summary = models.CharField("最后错误摘要", max_length=500, blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "雷达来源"
        verbose_name_plural = "雷达来源"

    def __str__(self) -> str:
        return self.name


class RadarItemQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_visible=True, published_at__lte=timezone.now())


class RadarItem(TimeStampedModel):
    class Kind(models.TextChoices):
        PAPER = "paper", "论文"
        REPOSITORY = "repository", "开源项目"
        MODEL = "model", "模型"
        ARTICLE = "article", "文章"

    source = models.ForeignKey(
        RadarSource, on_delete=models.PROTECT, related_name="items", verbose_name="来源"
    )
    external_id = models.CharField("外部 ID", max_length=200)
    kind = models.CharField("类型", max_length=20, choices=Kind.choices)
    title = models.CharField("标题", max_length=300)
    original_url = models.URLField("原文链接", max_length=500)
    summary = models.TextField("摘要", blank=True)
    ai_summary = models.JSONField("AI 摘要", default=dict, blank=True)
    authors = models.JSONField("作者", default=list, blank=True)
    metadata = models.JSONField("来源元数据", default=dict, blank=True)
    topics = models.ManyToManyField(Topic, blank=True, related_name="radar_items")
    published_at = models.DateTimeField("来源发布时间")
    fetched_at = models.DateTimeField("抓取时间", auto_now_add=True)
    relevance_score = models.DecimalField(
        "相关性", max_digits=5, decimal_places=2, default=0
    )
    is_featured = models.BooleanField("精选", default=False)
    is_visible = models.BooleanField("公开", default=True)
    is_demo = models.BooleanField("演示数据", default=False)

    objects = RadarItemQuerySet.as_manager()

    class Meta:
        ordering = ("-published_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "external_id"), name="radar_unique_source_external_id"
            )
        ]
        indexes = [
            models.Index(fields=("is_visible", "published_at")),
            models.Index(fields=("kind", "published_at")),
        ]
        verbose_name = "雷达条目"
        verbose_name_plural = "雷达条目"

    def __str__(self) -> str:
        return self.title


class IngestionRun(TimeStampedModel):
    class Status(models.TextChoices):
        RUNNING = "running", "运行中"
        SUCCESS = "success", "成功"
        PARTIAL = "partial", "部分成功"
        FAILED = "failed", "失败"
        SKIPPED = "skipped", "已跳过"

    source = models.ForeignKey(
        RadarSource,
        on_delete=models.PROTECT,
        related_name="ingestion_runs",
        blank=True,
        null=True,
        verbose_name="来源",
    )
    status = models.CharField("状态", max_length=16, choices=Status.choices)
    started_at = models.DateTimeField("开始时间", default=timezone.now)
    finished_at = models.DateTimeField("结束时间", blank=True, null=True)
    inserted_count = models.PositiveIntegerField("新增", default=0)
    updated_count = models.PositiveIntegerField("更新", default=0)
    skipped_count = models.PositiveIntegerField("跳过", default=0)
    error_count = models.PositiveIntegerField("错误", default=0)
    error_summary = models.TextField("错误摘要", blank=True)

    class Meta:
        ordering = ("-started_at",)
        verbose_name = "采集记录"
        verbose_name_plural = "采集记录"

    def __str__(self) -> str:
        return f"{self.source or '全部来源'} - {self.get_status_display()}"
