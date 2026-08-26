from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from . import richtext


class Article(models.Model):
    CATEGORY_CHOICES = [
        ("News", "News"),
        ("Economy", "Economy"),
        ("Technology", "Technology"),
        ("Environment", "Environment"),
        ("Education", "Education"),
        ("Blogs", "Blogs"),
        ("Sports", "Sports"),
        ("Updates", "Updates"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    dek = models.CharField(max_length=300, help_text="One-sentence summary shown on listings.")
    body = models.TextField(
        help_text=(
            "Leave a blank line between paragraphs. Paste a web address to link it, "
            "or write [words to link](https://example.com) to link a phrase. "
            "A YouTube address on a line of its own becomes a playable video."
        )
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="News")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="articles")
    allow_links = models.BooleanField(
        default=True,
        verbose_name="Make links in the story clickable",
        help_text="Turn off to show web addresses as plain text.",
    )
    embed_videos = models.BooleanField(
        default=True,
        verbose_name="Play YouTube links as videos",
        help_text="Turn off to show YouTube addresses as ordinary links instead of a player.",
    )
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "story"
            slug = base
            n = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:article_detail", args=[self.slug])

    def get_edit_url(self):
        return reverse("news:edit_article", args=[self.pk])

    # --- photos -----------------------------------------------------------
    # A story carries as many photos as it needs; exactly one of them is the
    # spotlight image used for the front page and the top of the story.

    @property
    def photo_list(self):
        # Memoised so a template can ask for the spotlight image, the gallery
        # and the count without three trips to the database.
        if not hasattr(self, "_photo_list_cache"):
            self._photo_list_cache = list(self.photos.all())
        return self._photo_list_cache

    @property
    def main_photo(self):
        photos = self.photo_list
        for photo in photos:
            if photo.is_main:
                return photo
        return photos[0] if photos else None

    @property
    def gallery_photos(self):
        """Every photo except the spotlight one."""
        main = self.main_photo
        return [photo for photo in self.photo_list if photo != main]

    @property
    def photo_count(self):
        return len(self.photo_list)

    def set_main_photo(self, photo):
        """Make ``photo`` the spotlight image and demote every other photo."""
        if photo is None or photo.article_id != self.pk:
            return
        self.photos.exclude(pk=photo.pk).filter(is_main=True).update(is_main=False)
        if not photo.is_main:
            photo.is_main = True
            photo.save(update_fields=["is_main"])

    def ensure_main_photo(self):
        """Guarantee that a story with photos has exactly one spotlight image."""
        photos = list(self.photos.all())
        if not photos:
            return
        mains = [photo for photo in photos if photo.is_main]
        if len(mains) == 1:
            return
        self.set_main_photo(mains[0] if mains else photos[0])

    # --- body -------------------------------------------------------------

    @property
    def body_html(self):
        return richtext.render_body(
            self.body, allow_links=self.allow_links, embed_videos=self.embed_videos
        )

    @property
    def has_video(self):
        return self.embed_videos and bool(richtext.find_videos(self.body, limit=1))


class ArticlePhoto(models.Model):
    """One of the photos attached to a story."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="articles/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(
        default=False, help_text="The spotlight image shown on the front page."
    )
    position = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-is_main", "position", "id"]

    def __str__(self):
        return self.caption or f"Photo for {self.article_id}"
