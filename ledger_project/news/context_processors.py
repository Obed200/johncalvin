from .models import Article


def navigation(request):
    """The section list, so the masthead nav stays in step with the model."""
    return {"nav_categories": [choice[0] for choice in Article.CATEGORY_CHOICES]}
