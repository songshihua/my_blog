from django.db import models

from apps.core.models import TimeStampedModel, Topic


class Project(TimeStampedModel):
    class Category(models.TextChoices):
        INFERENCE = "inference", "推理优化"
        SYSTEM = "system", "系统实践"
        TOOL = "tool", "工具"
        LEARNING = "learning", "学习实验"

    title = models.CharField("标题", max_length=160)
    slug = models.SlugField("标识", max_length=180, unique=True)
    subtitle = models.CharField("副标题", max_length=200, blank=True)
    category = models.CharField(
        "分类", max_length=24, choices=Category.choices, default=Category.INFERENCE
    )
    summary = models.TextField("摘要")
    problem = models.TextField("研究问题", blank=True)
    approach = models.TextField("设计思路", blank=True)
    contribution = models.TextField("个人贡献", blank=True)
    outcome = models.TextField("结果", blank=True)
    repository_url = models.URLField("代码仓库", blank=True)
    demo_url = models.URLField("演示链接", blank=True)
    topics = models.ManyToManyField(Topic, blank=True, related_name="projects")
    is_featured = models.BooleanField("精选", default=False)
    is_published = models.BooleanField("公开", default=False)
    is_demo = models.BooleanField("演示数据", default=False)
    sort_order = models.PositiveIntegerField("排序", default=0)
    started_at = models.DateField("开始日期", blank=True, null=True)
    ended_at = models.DateField("结束日期", blank=True, null=True)

    class Meta:
        ordering = ("sort_order", "-updated_at")
        indexes = [models.Index(fields=("is_published", "is_featured", "sort_order"))]
        verbose_name = "项目"
        verbose_name_plural = "项目"

    def __str__(self) -> str:
        return self.title
