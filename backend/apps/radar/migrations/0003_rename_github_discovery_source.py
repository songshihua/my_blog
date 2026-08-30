from django.db import migrations


OLD_NAMES = ("GitHub Projects", "GitHub Trending")
DISCOVERY_NAME = "GitHub 热门项目"
DISCOVERY_URL = "https://github.com/search?q=llm&type=repositories"


def rename_github_source(apps, _schema_editor):
    radar_source = apps.get_model("radar", "RadarSource")
    radar_source.objects.filter(
        source_type="github",
        name__in=OLD_NAMES,
    ).update(name=DISCOVERY_NAME, homepage_url=DISCOVERY_URL)


def restore_github_source_name(apps, _schema_editor):
    radar_source = apps.get_model("radar", "RadarSource")
    radar_source.objects.filter(
        source_type="github",
        name=DISCOVERY_NAME,
    ).update(name="GitHub Projects", homepage_url="https://github.com/")


class Migration(migrations.Migration):
    dependencies = [
        ("radar", "0002_radarsource_last_attempt_at_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_github_source, restore_github_source_name),
    ]
