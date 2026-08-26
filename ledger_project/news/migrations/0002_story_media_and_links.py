import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="allow_links",
            field=models.BooleanField(
                default=True,
                help_text="Turn off to show web addresses as plain text.",
                verbose_name="Make links in the story clickable",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="embed_videos",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Turn off to show YouTube addresses as ordinary links instead of a player."
                ),
                verbose_name="Play YouTube links as videos",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="body",
            field=models.TextField(
                help_text=(
                    "Leave a blank line between paragraphs. Paste a web address to link it, "
                    "or write [words to link](https://example.com) to link a phrase. "
                    "A YouTube address on a line of its own becomes a playable video."
                )
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="category",
            field=models.CharField(
                choices=[
                    ("News", "News"),
                    ("Economy", "Economy"),
                    ("Technology", "Technology"),
                    ("Environment", "Environment"),
                    ("Education", "Education"),
                    ("Blogs", "Blogs"),
                    ("Sports", "Sports"),
                    ("Updates", "Updates"),
                ],
                default="News",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="ArticlePhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="articles/%Y/%m/")),
                ("caption", models.CharField(blank=True, max_length=200)),
                (
                    "is_main",
                    models.BooleanField(
                        default=False, help_text="The spotlight image shown on the front page."
                    ),
                ),
                ("position", models.PositiveIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="news.article",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_main", "position", "id"],
            },
        ),
    ]
