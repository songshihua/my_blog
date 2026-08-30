from django.db import migrations


def normalize_note_hierarchy(apps, _schema_editor):
    """Normalize legacy flat demo categories without losing linked articles."""

    category_model = apps.get_model("blog", "Category")
    article_model = apps.get_model("blog", "Article")

    def upsert(*, slug, name, parent=None, sort_order=10):
        canonical = category_model.objects.filter(slug=slug).first()
        duplicate = category_model.objects.filter(name=name).exclude(
            pk=getattr(canonical, "pk", None)
        ).first()

        if canonical is None and duplicate is not None:
            duplicate.slug = slug
            duplicate.parent = parent
            duplicate.sort_order = sort_order
            duplicate.save(
                update_fields=("slug", "parent", "sort_order", "updated_at")
            )
            return duplicate

        if canonical is None:
            return category_model.objects.create(
                slug=slug,
                name=name,
                parent=parent,
                sort_order=sort_order,
            )

        if duplicate is not None:
            article_model.objects.filter(category=duplicate).update(category=canonical)
            category_model.objects.filter(parent=duplicate).update(parent=canonical)
            duplicate.delete()

        canonical.name = name
        canonical.parent = parent
        canonical.sort_order = sort_order
        canonical.save(update_fields=("name", "parent", "sort_order", "updated_at"))
        return canonical

    ai = upsert(slug="ai-technology", name="AI 技术")
    models = upsert(slug="large-models", name="大模型", parent=ai)
    inference = upsert(
        slug="inference-optimization",
        name="推理优化",
        parent=models,
    )
    notes = upsert(slug="notes", name="学习笔记", parent=inference)

    legacy = category_model.objects.filter(slug="learning-notes").exclude(pk=notes.pk)
    for duplicate in legacy:
        article_model.objects.filter(category=duplicate).update(category=notes)
        category_model.objects.filter(parent=duplicate).update(parent=notes)
        duplicate.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_articlesourcefile_category_parent_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_note_hierarchy, migrations.RunPython.noop),
    ]
