import uuid

import apps.blog.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0003_normalize_note_hierarchy"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticleImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "public_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "file",
                    models.ImageField(
                        max_length=240,
                        upload_to=apps.blog.models.note_image_upload_to,
                        verbose_name="图片",
                    ),
                ),
                ("original_filename", models.CharField(max_length=240, verbose_name="原文件名")),
                ("content_type", models.CharField(max_length=40, verbose_name="内容类型")),
                ("size_bytes", models.PositiveBigIntegerField(verbose_name="文件大小")),
                ("width", models.PositiveIntegerField(verbose_name="宽度")),
                ("height", models.PositiveIntegerField(verbose_name="高度")),
                (
                    "article",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="blog.article",
                        verbose_name="所属文章",
                    ),
                ),
            ],
            options={
                "verbose_name": "笔记图片",
                "verbose_name_plural": "笔记图片",
                "ordering": ("-created_at",),
            },
        ),
    ]
