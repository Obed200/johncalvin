import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Article, ArticlePhoto
from .richtext import find_videos, render_body, youtube_video

User = get_user_model()

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="ledger-tests-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaTestCase(TestCase):
    """Keeps photos uploaded by tests out of the project's media folder."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


def photo_file(name="photo.png", color=(120, 140, 160)):
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


class RichTextTests(TestCase):
    def test_bare_url_becomes_a_link(self):
        html = render_body("Read https://example.com/report today.")
        self.assertIn('href="https://example.com/report"', html)
        self.assertIn('rel="noopener noreferrer nofollow"', html)
        # The full stop is sentence punctuation, not part of the address.
        self.assertNotIn("report.&quot;", html)
        self.assertIn("today.", html)

    def test_labelled_link(self):
        html = render_body("See [the full report](https://example.com/r) for detail.")
        self.assertIn('href="https://example.com/r"', html)
        self.assertIn(">the full report</a>", html)

    def test_www_links_get_a_scheme(self):
        html = render_body("Visit www.example.com now.")
        self.assertIn('href="https://www.example.com"', html)

    def test_unsafe_schemes_are_not_linked(self):
        html = render_body("[click](javascript:alert(1))")
        self.assertNotIn("<a", html)
        self.assertNotIn("javascript:alert(1)</a>", html)

    def test_markup_in_the_body_is_escaped(self):
        html = render_body("<script>alert('x')</script> and <b>bold</b>")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_links_can_be_switched_off(self):
        html = render_body("Read https://example.com/report", allow_links=False)
        self.assertNotIn("<a", html)
        self.assertIn("https://example.com/report", html)

    def test_youtube_link_on_its_own_line_is_embedded(self):
        html = render_body("Intro\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ\nOutro")
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", html)
        self.assertIn("<iframe", html)
        self.assertIn("<p>Intro</p>", html)

    def test_embedded_video_can_be_captioned(self):
        html = render_body("[Site tour](https://youtu.be/dQw4w9WgXcQ)")
        self.assertIn("<iframe", html)
        self.assertIn("<figcaption>Site tour</figcaption>", html)

    def test_video_embedding_can_be_switched_off(self):
        html = render_body("https://youtu.be/dQw4w9WgXcQ", embed_videos=False)
        self.assertNotIn("<iframe", html)
        self.assertIn('href="https://youtu.be/dQw4w9WgXcQ"', html)

    def test_youtube_link_inside_a_sentence_stays_a_link(self):
        html = render_body("We covered it here https://youtu.be/dQw4w9WgXcQ last week.")
        self.assertNotIn("<iframe", html)
        self.assertIn("<a", html)

    def test_start_time_is_carried_into_the_embed(self):
        html = render_body("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s")
        self.assertIn("start=90", html)

    def test_youtube_video_ids(self):
        self.assertEqual(youtube_video("https://youtu.be/dQw4w9WgXcQ")[0], "dQw4w9WgXcQ")
        self.assertEqual(youtube_video("https://www.youtube.com/shorts/dQw4w9WgXcQ")[0], "dQw4w9WgXcQ")
        self.assertIsNone(youtube_video("https://vimeo.com/12345"))
        self.assertIsNone(youtube_video("https://example.com/watch?v=dQw4w9WgXcQ"))

    def test_find_videos_lists_each_video_once(self):
        body = "https://youtu.be/dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(len(find_videos(body)), 1)


class ArticleModelTests(MediaTestCase):
    def setUp(self):
        self.author = User.objects.create_user("writer", password="pw12345678")
        self.article = Article.objects.create(
            title="A story", dek="A summary", body="Text", author=self.author
        )

    def test_default_category_is_news(self):
        self.assertEqual(self.article.category, "News")

    def test_categories_cover_the_published_sections(self):
        self.assertEqual(
            [c[0] for c in Article.CATEGORY_CHOICES],
            ["News", "Economy", "Technology", "Environment", "Education", "Blogs", "Sports", "Updates"],
        )

    def test_main_photo_falls_back_to_the_first_photo(self):
        first = ArticlePhoto.objects.create(article=self.article, image=photo_file("a.png"), position=0)
        ArticlePhoto.objects.create(article=self.article, image=photo_file("b.png"), position=1)
        self.assertEqual(self.article.main_photo, first)

    def test_setting_a_main_photo_demotes_the_others(self):
        first = ArticlePhoto.objects.create(
            article=self.article, image=photo_file("a.png"), position=0, is_main=True
        )
        second = ArticlePhoto.objects.create(article=self.article, image=photo_file("b.png"), position=1)

        self.article.set_main_photo(second)
        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_main)
        self.assertTrue(second.is_main)
        self.assertEqual(Article.objects.get(pk=self.article.pk).main_photo, second)

    def test_gallery_excludes_the_spotlight_photo(self):
        ArticlePhoto.objects.create(article=self.article, image=photo_file("a.png"), is_main=True)
        extra = ArticlePhoto.objects.create(article=self.article, image=photo_file("b.png"))
        self.assertEqual(self.article.gallery_photos, [extra])
        self.assertEqual(self.article.photo_count, 2)

    def test_has_video_follows_the_embed_switch(self):
        self.article.body = "https://youtu.be/dQw4w9WgXcQ"
        self.assertTrue(self.article.has_video)
        self.article.embed_videos = False
        self.assertFalse(self.article.has_video)


class PublishingViewTests(MediaTestCase):
    def setUp(self):
        self.author = User.objects.create_user("writer", password="pw12345678")
        self.other = User.objects.create_user("someone", password="pw12345678")
        self.client.force_login(self.author)

    def publish(self, **overrides):
        data = {
            "title": "Grid rebuild begins",
            "dek": "A summary of the story.",
            "category": "Environment",
            "body": "Body text with https://example.com/report inside.",
            "allow_links": "on",
            "embed_videos": "on",
            "photos": [photo_file("a.png"), photo_file("b.png"), photo_file("c.png")],
            "main_photo_index": "1",
        }
        data.update(overrides)
        return self.client.post(reverse("news:author_dashboard"), data)

    def test_publishing_stores_every_photo_and_the_chosen_spotlight(self):
        response = self.publish()
        self.assertEqual(response.status_code, 302)

        article = Article.objects.get(title="Grid rebuild begins")
        self.assertEqual(article.photo_count, 3)
        self.assertEqual(article.main_photo.position, 1)
        self.assertEqual(article.photos.filter(is_main=True).count(), 1)

    def test_publishing_without_photos_is_allowed(self):
        self.publish(photos=[])
        article = Article.objects.get(title="Grid rebuild begins")
        self.assertIsNone(article.main_photo)

    def test_an_out_of_range_spotlight_choice_falls_back_to_the_first(self):
        self.publish(main_photo_index="9")
        article = Article.objects.get(title="Grid rebuild begins")
        self.assertEqual(article.main_photo.position, 0)

    def test_switches_are_saved(self):
        self.publish(allow_links="", embed_videos="")
        article = Article.objects.get(title="Grid rebuild begins")
        self.assertFalse(article.allow_links)
        self.assertFalse(article.embed_videos)

    def test_detail_page_renders_links_photos_and_gallery(self):
        self.publish(body="Read https://example.com/report\nhttps://youtu.be/dQw4w9WgXcQ")
        article = Article.objects.get(title="Grid rebuild begins")

        response = self.client.get(article.get_absolute_url())
        self.assertContains(response, 'href="https://example.com/report"')
        self.assertContains(response, "youtube-nocookie.com/embed/dQw4w9WgXcQ")
        self.assertContains(response, "More photos")

    def test_front_page_links_the_photo_and_the_headline(self):
        self.publish()
        article = Article.objects.get(title="Grid rebuild begins")

        response = self.client.get(reverse("news:home"))
        html = response.content.decode()
        tease = f'<a class="story-tease hero-tease" href="{article.get_absolute_url()}">'
        self.assertIn(tease, html)
        # The photo sits inside that same link, so the image opens the story too.
        self.assertIn("3 photos", html)

    def test_category_filter_uses_the_new_sections(self):
        self.publish()
        response = self.client.get(reverse("news:home"), {"category": "Environment"})
        self.assertContains(response, "Grid rebuild begins")
        response = self.client.get(reverse("news:home"), {"category": "Sports"})
        self.assertNotContains(response, "Grid rebuild begins")

    def test_author_can_edit_photos_and_pick_a_new_spotlight(self):
        self.publish()
        article = Article.objects.get(title="Grid rebuild begins")
        photos = list(article.photos.all().order_by("position"))

        response = self.client.post(
            reverse("news:edit_article", args=[article.pk]),
            {
                "title": article.title,
                "dek": article.dek,
                "category": "News",
                "body": article.body,
                "allow_links": "on",
                "embed_videos": "on",
                "photos-TOTAL_FORMS": "3",
                "photos-INITIAL_FORMS": "3",
                "photos-MIN_NUM_FORMS": "0",
                "photos-MAX_NUM_FORMS": "1000",
                "photos-0-id": str(photos[0].pk),
                "photos-0-caption": "The old substation",
                "photos-1-id": str(photos[1].pk),
                "photos-1-caption": "",
                "photos-2-id": str(photos[2].pk),
                "photos-2-caption": "",
                "photos-2-DELETE": "on",
                "main_photo": str(photos[0].pk),
            },
        )
        self.assertEqual(response.status_code, 302)

        article.refresh_from_db()
        self.assertEqual(article.category, "News")
        self.assertEqual(article.photo_count, 2)
        self.assertEqual(article.main_photo.pk, photos[0].pk)
        self.assertEqual(article.main_photo.caption, "The old substation")

    def test_another_author_cannot_edit_the_story(self):
        self.publish()
        article = Article.objects.get(title="Grid rebuild begins")

        self.client.force_login(self.other)
        response = self.client.get(reverse("news:edit_article", args=[article.pk]))
        self.assertRedirects(response, reverse("news:home"))
