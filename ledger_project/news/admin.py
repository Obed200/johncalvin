from django.contrib import admin

from .models import Article, ArticlePhoto


class ArticlePhotoInline(admin.TabularInline):
    model = ArticlePhoto
    extra = 1
    fields = ("image", "caption", "is_main", "position")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "featured", "photo_count", "created_at")
    list_filter = ("category", "featured", "allow_links", "embed_videos")
    search_fields = ("title", "dek", "body")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ArticlePhotoInline]

    @admin.display(description="Photos")
    def photo_count(self, obj):
        return obj.photos.count()


@admin.register(ArticlePhoto)
class ArticlePhotoAdmin(admin.ModelAdmin):
    list_display = ("article", "caption", "is_main", "position")
    list_filter = ("is_main",)
