from django import forms
from django.core.exceptions import ValidationError

from .models import Article, ArticlePhoto

# A generous ceiling so a photo-heavy story is fine while a runaway upload
# is not. Authors can add more photos afterwards from the edit page.
MAX_PHOTOS_PER_UPLOAD = 20


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that accepts however many files the author picked."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True, "accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        clean_one = super().clean
        if not data:
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        if len(data) > MAX_PHOTOS_PER_UPLOAD:
            raise ValidationError(
                f"You can upload up to {MAX_PHOTOS_PER_UPLOAD} photos at a time — "
                "add the rest by editing the story afterwards."
            )
        return [clean_one(item, initial) for item in data]


class ArticleForm(forms.ModelForm):
    photos = MultipleImageField(
        required=False,
        label="Photos",
        help_text=(
            "Pick as many photos as the story needs. One of them becomes the "
            "spotlight image used on the front page."
        ),
    )
    # Which of the newly picked files is the spotlight image. The dashboard
    # sets this from the photo picker; without JavaScript the first one wins.
    main_photo_index = forms.IntegerField(required=False, min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = Article
        fields = ["title", "dek", "category", "body", "allow_links", "embed_videos"]
        widgets = {
            "dek": forms.Textarea(attrs={"rows": 2}),
            "body": forms.Textarea(attrs={"rows": 14}),
        }

    def clean_main_photo_index(self):
        index = self.cleaned_data.get("main_photo_index") or 0
        uploads = self.cleaned_data.get("photos") or []
        return index if index < len(uploads) else 0

    def save_photos(self, article):
        """Attach the uploaded files to ``article``, keeping one spotlight image."""
        uploads = self.cleaned_data.get("photos") or []
        if not uploads:
            article.ensure_main_photo()
            return []

        chosen = self.cleaned_data.get("main_photo_index") or 0
        start = article.photos.count()
        had_main = article.photos.filter(is_main=True).exists()

        created = []
        for offset, upload in enumerate(uploads):
            created.append(
                ArticlePhoto.objects.create(
                    article=article,
                    image=upload,
                    position=start + offset,
                )
            )
        if not had_main and created:
            article.set_main_photo(created[min(chosen, len(created) - 1)])
        else:
            article.ensure_main_photo()
        return created


ArticlePhotoFormSet = forms.inlineformset_factory(
    Article,
    ArticlePhoto,
    fields=["caption"],
    extra=0,
    can_delete=True,
    widgets={"caption": forms.TextInput(attrs={"placeholder": "Caption (optional)"})},
)
