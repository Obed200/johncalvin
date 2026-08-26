from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ("role", "bio", "avatar")


class LedgerUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "first_name", "email", "role", "is_staff")

    def role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, "profile") else "—"


admin.site.unregister(User)
admin.site.register(User, LedgerUserAdmin)
