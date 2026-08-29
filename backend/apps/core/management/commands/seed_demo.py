"""Create clearly labelled sample records for local UI development."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.blog.models import Article, Category
from apps.core.models import SiteProfile, Topic
from apps.portfolio.models import Project
from apps.radar.models import RadarItem, RadarSource


class Command(BaseCommand):
    help = "Create or update idempotent local sample data. Never use as claimed results."

    def handle(self, *args, **options):
        now = timezone.now()

        topics = {}
        for sort_order, (name, slug) in enumerate(
            (
                ("Speculative Decoding", "speculative-decoding"),
                ("KV Cache", "kv-cache"),
                ("LLM Serving", "llm-serving"),
                ("Continuous Batching", "continuous-batching"),
                ("Quantization", "quantization"),
                ("Long Context", "long-context"),
            )
        ):
            topics[slug], _ = Topic.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "sort_order": sort_order, "color": "#315CFF"},
            )

        profile, _ = SiteProfile.objects.update_or_create(
            name="宋世华",
            defaults={
                "english_name": "Shihua Song",
                "headline": "让大模型推理更快、更省、更稳。",
                "bio": "专注于大模型推理优化与高性能服务系统。",
                "affiliation": "北京交通大学",
                "role": "硕士研究生",
                "research_focus": "投机解码、KV Cache 与高性能 LLM Serving",
                "github_url": "https://github.com/songshihua/",
                "email": "",
                "seo_description": "大模型推理优化研究、项目实践与学习笔记。",
                "is_active": True,
            },
        )
        self.stdout.write(f"Profile ready: {profile}")

        project_specs = (
            {
                "slug": "spec-decode-lab-sample",
                "title": "SpecDecode Lab",
                "subtitle": "投机解码实验工作台",
                "category": Project.Category.INFERENCE,
                "summary": "用于理解候选生成、目标验证与接受/拒绝流程的界面示例。",
                "problem": "如何在保证输出质量的前提下理解投机解码的关键环节？",
                "approach": "以可交互流程图拆解 Draft、Verify 与 Accept/Reject。",
                "outcome": "当前仅包含界面演示数据，不代表真实实验结论。",
                "topics": ("speculative-decoding", "llm-serving"),
            },
            {
                "slug": "kv-cache-observatory-sample",
                "title": "KV Cache Observatory",
                "subtitle": "显存与吞吐分析面板",
                "category": Project.Category.SYSTEM,
                "summary": "观察 KV Cache 分配、命中率与序列长度关系的概念面板。",
                "problem": "KV Cache 如何随上下文长度与并发变化？",
                "approach": "使用矩阵和时间线呈现缓存占用状态。",
                "outcome": "图表为示意数据，需要接入真实实验后才可作为成果。",
                "topics": ("kv-cache", "long-context"),
            },
            {
                "slug": "llm-serving-notes-sample",
                "title": "LLM Serving Notes",
                "subtitle": "推理优化知识图谱",
                "category": Project.Category.LEARNING,
                "summary": "整理调度、批处理、系统资源与模型优化之间的关系。",
                "problem": "推理系统的关键优化模块如何协同？",
                "approach": "建立可持续更新的概念图与工程笔记。",
                "outcome": "目前为学习型概念项目。",
                "topics": ("llm-serving", "continuous-batching", "quantization"),
            },
        )
        for order, spec in enumerate(project_specs):
            topic_slugs = spec.pop("topics")
            project, _ = Project.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    **spec,
                    "is_featured": True,
                    "is_published": True,
                    "is_demo": True,
                    "sort_order": order,
                    "repository_url": "https://github.com/songshihua/",
                },
            )
            project.topics.set(topics[slug] for slug in topic_slugs)

        category, _ = Category.objects.update_or_create(
            slug="learning-notes",
            defaults={"name": "学习笔记", "description": "大模型推理优化学习记录"},
        )
        article_specs = (
            (
                "speculative-decoding-acceptance-sample",
                "投机解码中的接受率、延迟与吞吐",
                "从核心直觉到系统指标，理解投机解码为何能够加速生成。",
                "speculative-decoding",
            ),
            (
                "kv-cache-memory-sample",
                "KV Cache 的显存瓶颈与优化思路",
                "梳理长上下文推理中的缓存占用、复用与调度问题。",
                "kv-cache",
            ),
            (
                "continuous-batching-sample",
                "Continuous Batching 调度笔记",
                "记录动态批处理的吞吐、排队与公平性权衡。",
                "continuous-batching",
            ),
        )
        for index, (slug, title, summary, topic_slug) in enumerate(article_specs):
            article, _ = Article.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "summary": summary,
                    "body_markdown": (
                        "# 界面示例\n\n"
                        "本文用于本地界面与 API 联调，内容和曲线均为演示数据。\n\n"
                        "## 核心直觉\n\nDraft 模型生成候选，Target 模型负责并行验证。"
                    ),
                    "category": category,
                    "status": Article.Status.PUBLISHED,
                    "published_at": now - timedelta(days=index * 3),
                    "reading_minutes": 8 - index,
                    "repository_url": "https://github.com/songshihua/",
                    "is_featured": index == 0,
                    "is_demo": True,
                },
            )
            article.topics.set((topics[topic_slug],))

        source_specs = (
            ("arxiv", "arXiv API", "https://arxiv.org/", "paper"),
            ("huggingface", "Hugging Face", "https://huggingface.co/", "model"),
            ("github", "GitHub Trending", "https://github.com/", "repository"),
            ("openreview", "OpenReview", "https://openreview.net/", "paper"),
        )
        for index, (source_type, name, url, kind) in enumerate(source_specs):
            source, _ = RadarSource.objects.update_or_create(
                source_type=source_type,
                defaults={
                    "name": name,
                    "homepage_url": url,
                    "is_enabled": False,
                    "status": RadarSource.Status.DISABLED,
                },
            )
            item, _ = RadarItem.objects.update_or_create(
                source=source,
                external_id=f"sample-{source_type}-001",
                defaults={
                    "kind": kind,
                    "title": (
                        "Fast Speculative Decoding for Production LLM Serving"
                        if index == 0
                        else f"{name} · 本地演示条目"
                    ),
                    "original_url": url,
                    "summary": "仅用于呈现筛选、折叠与 AI 摘要界面，不代表真实收录内容。",
                    "ai_summary": {
                        "核心贡献": "界面示例：展示结构化摘要区域。",
                        "实验结论": "示意数据：未连接真实外部来源。",
                        "相关方向": "大模型推理优化。",
                    },
                    "authors": ["Sample Author"],
                    "metadata": {"sample": True},
                    "published_at": now - timedelta(hours=index * 3),
                    "relevance_score": 90 - index * 5,
                    "is_featured": index == 0,
                    "is_visible": True,
                    "is_demo": True,
                },
            )
            item.topics.set((topics["speculative-decoding"],))

        self.stdout.write(self.style.SUCCESS("Local sample data is ready (all samples labelled)."))
