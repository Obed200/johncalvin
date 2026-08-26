from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile

User = get_user_model()


class CreateAuthorForm(UserCreationForm):
    """Used by administrators to create a new author account, complete with
    an optional profile photo — this is the form behind 'Create author account'."""

    first_name = forms.CharField(max_length=150, required=True, label="Full name")
    email = forms.EmailField(required=False)
    bio = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Short bio",
        help_text="Shown under the author's byline, e.g. 'Covers markets and monetary policy.'",
    )
    avatar = forms.ImageField(required=False, label="Author photo")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.last_name = ""
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = "author"
            profile.bio = self.cleaned_data.get("bio", "")
            if self.cleaned_data.get("avatar"):
                profile.avatar = self.cleaned_data["avatar"]
            profile.save()
        return user
