from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from news.models import Article

from .forms import CreateAuthorForm
from .models import Profile

User = get_user_model()


def is_admin_user(user):
    return user.is_authenticated and (
        user.is_superuser or user.is_staff or getattr(getattr(user, "profile", None), "is_admin", False)
    )


@login_required
@user_passes_test(is_admin_user, login_url="accounts:login")
def admin_dashboard(request):
    if request.method == "POST":
        form = CreateAuthorForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Author account created. {user.first_name} can sign in with username "{user.username}".',
            )
            return redirect("accounts:admin_dashboard")
    else:
        form = CreateAuthorForm()

    authors = Profile.objects.select_related("user").filter(role="author")
    articles = Article.objects.select_related("author", "author__profile").prefetch_related("photos")
    return render(
        request,
        "accounts/admin_dashboard.html",
        {"form": form, "authors": authors, "articles": articles},
    )


@login_required
@user_passes_test(is_admin_user, login_url="accounts:login")
def remove_author(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, "You can't remove the account you're signed in with.")
    else:
        target.delete()
        messages.success(request, "Account removed. Their existing stories stay published.")
    return redirect("accounts:admin_dashboard")
