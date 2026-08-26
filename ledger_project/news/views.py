from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import Profile
from accounts.views import is_admin_user

from .forms import ArticleForm, ArticlePhotoFormSet
from .models import Article, ArticlePhoto

CATEGORIES = [choice[0] for choice in Article.CATEGORY_CHOICES]


def published_articles():
    return Article.objects.select_related("author", "author__profile").prefetch_related("photos")


def home(request):
    category = request.GET.get("category")
    articles = published_articles()
    if category in CATEGORIES:
        articles = articles.filter(category=category)

    featured = articles.filter(featured=True).first() or articles.first()
    rest = list(articles.exclude(pk=featured.pk)) if featured else []

    context = {
        "featured": featured,
        "side_stories": rest[:3],
        "grid_stories": rest[3:9],
        "categories": CATEGORIES,
        "active_category": category if category in CATEGORIES else "All",
        "authors": Profile.objects.select_related("user").filter(role="author"),
    }
    return render(request, "news/home.html", context)


def article_detail(request, slug):
    article = get_object_or_404(published_articles(), slug=slug)
    return render(request, "news/article_detail.html", {"article": article})


def can_edit(user, article):
    return article.author == user or is_admin_user(user)


@login_required
def author_dashboard(request):
    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            photos = form.save_photos(article)
            note = f" with {len(photos)} photo{'s' if len(photos) != 1 else ''}" if photos else ""
            messages.success(request, f"Story published to The Ledger{note}.")
            return redirect("news:author_dashboard")
        messages.error(request, "The story could not be published — please check the form below.")
    else:
        form = ArticleForm()

    mine = Article.objects.filter(author=request.user).prefetch_related("photos")
    return render(request, "news/author_dashboard.html", {"form": form, "articles": mine})


@login_required
def edit_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if not can_edit(request.user, article):
        messages.error(request, "You can only edit your own stories.")
        return redirect("news:home")

    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, instance=article)
        formset = ArticlePhotoFormSet(request.POST, instance=article)
        if form.is_valid() and formset.is_valid():
            article = form.save()
            formset.save()
            form.save_photos(article)

            # The spotlight radio names an existing photo; a photo just deleted
            # or belonging to another story is ignored.
            main_pk = request.POST.get("main_photo", "")
            if main_pk.isdigit():
                chosen = ArticlePhoto.objects.filter(pk=main_pk, article=article).first()
                if chosen:
                    article.set_main_photo(chosen)
            article.ensure_main_photo()

            messages.success(request, "Story updated.")
            return redirect("news:edit_article", pk=article.pk)
        messages.error(request, "The story could not be saved — please check the form below.")
    else:
        form = ArticleForm(instance=article)
        formset = ArticlePhotoFormSet(instance=article)

    return render(
        request,
        "news/article_edit.html",
        {"form": form, "formset": formset, "article": article},
    )


@login_required
def delete_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if not can_edit(request.user, article):
        messages.error(request, "You can only delete your own stories.")
    else:
        article.delete()
        messages.success(request, "Story deleted.")
    back = request.META.get("HTTP_REFERER")
    if back and url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        return redirect(back)
    return redirect("news:home")


@login_required
def toggle_featured(request, pk):
    if not is_admin_user(request.user):
        messages.error(request, "Only administrators can feature a story.")
        return redirect("news:home")
    article = get_object_or_404(Article, pk=pk)
    article.featured = not article.featured
    article.save()
    return redirect("accounts:admin_dashboard")
