"""Shared content models."""

from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    """Consistent audit timestamps for authored content."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Topic(TimeStampedModel):
    name = models.CharField("名称", max_length=80, unique=True)
    slug = models.SlugField("标识", max_length=100, unique=True)
    description = models.CharField("描述", max_length=240, blank=True)
    color = models.CharField("颜色", max_length=20, default="#315CFF")
    sort_order = models.PositiveIntegerField("排序", default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "研究主题"
        verbose_name_plural = "研究主题"

    def __str__(self) -> str:
        return self.name


class SiteProfile(TimeStampedModel):
    """Singleton-style public profile maintained through Django Admin."""

    name = models.CharField("姓名", max_length=80)
    english_name = models.CharField("英文名", max_length=120, blank=True)
    headline = models.CharField("一句话介绍", max_length=180)
    bio = models.TextField("个人简介", blank=True)
    affiliation = models.CharField("学校/机构", max_length=180)
    role = models.CharField("身份", max_length=120, blank=True)
    research_focus = models.CharField("研究方向", max_length=240)
    github_url = models.URLField("GitHub", blank=True)
    email = models.EmailField("联系邮箱", blank=True)
    seo_description = models.CharField("SEO 描述", max_length=240, blank=True)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "个人档案"
        verbose_name_plural = "个人档案"

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.is_active:
            duplicate = SiteProfile.objects.filter(is_active=True).exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError("只能启用一份个人档案。")
