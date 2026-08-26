from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("", views.home, name="home"),
    path("story/<slug:slug>/", views.article_detail, name="article_detail"),
    path("dashboard/", views.author_dashboard, name="author_dashboard"),
    path("dashboard/edit/<int:pk>/", views.edit_article, name="edit_article"),
    path("dashboard/delete/<int:pk>/", views.delete_article, name="delete_article"),
    path("dashboard/feature/<int:pk>/", views.toggle_featured, name="toggle_featured"),
]
