from django.db import migrations


class Migration(migrations.Migration):
    """Drops the single cover photo — migration 0003 copied it into
    news.ArticlePhoto, where it is the story's spotlight image."""

    dependencies = [
        ("news", "0003_move_photos_and_categories"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="article",
            name="image",
        ),
    ]
