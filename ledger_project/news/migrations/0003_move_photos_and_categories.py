"""Carries existing stories over to the new sections and photo gallery.

The old five business sections map onto the new eight; the single cover photo
each story could have becomes its spotlight photo in the gallery.
"""

from django.db import migrations

# Old category -> new category.
CATEGORY_MAP = {
    "Business": "Economy",
    "Markets": "Economy",
    "Money": "Economy",
    "Leadership": "Blogs",
    "Technology": "Technology",
}
REVERSE_MAP = {
    "Economy": "Business",
    "Blogs": "Leadership",
    "Technology": "Technology",
    "News": "Business",
    "Environment": "Business",
    "Education": "Leadership",
    "Sports": "Business",
    "Updates": "Business",
}


def forwards(apps, schema_editor):
    Article = apps.get_model("news", "Article")
    ArticlePhoto = apps.get_model("news", "ArticlePhoto")

    for old, new in CATEGORY_MAP.items():
        Article.objects.filter(category=old).update(category=new)
    Article.objects.exclude(
        category__in=["News", "Economy", "Technology", "Environment", "Education", "Blogs", "Sports", "Updates"]
    ).update(category="News")

    for article in Article.objects.exclude(image="").exclude(image=None):
        ArticlePhoto.objects.create(article=article, image=article.image.name, is_main=True, position=0)


def backwards(apps, schema_editor):
    Article = apps.get_model("news", "Article")
    ArticlePhoto = apps.get_model("news", "ArticlePhoto")

    for photo in ArticlePhoto.objects.filter(is_main=True).select_related("article"):
        if not photo.article.image:
            photo.article.image = photo.image.name
            photo.article.save(update_fields=["image"])

    for article in Article.objects.all():
        article.category = REVERSE_MAP.get(article.category, "Business")
        article.save(update_fields=["category"])


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0002_story_media_and_links"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
