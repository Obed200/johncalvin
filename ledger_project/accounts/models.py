from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Extra information about a user: their role at The Ledger, bio and photo."""

    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("author", "Author"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="author")
    bio = models.TextField(blank=True, help_text="One or two sentences shown on the author's byline.")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    class Meta:
        ordering = ["user__first_name", "user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == "admin" or self.user.is_superuser

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Every user gets a Profile automatically. Superusers/staff created via
    createsuperuser are treated as administrators; everyone else starts as an author."""
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={"role": "admin" if (instance.is_superuser or instance.is_staff) else "author"},
        )
