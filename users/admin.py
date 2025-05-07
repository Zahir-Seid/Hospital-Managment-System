from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from users.models import User

class CustomUserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    list_display = (
        "username", "email", "role", "is_staff", "is_active",
    )
    list_filter = ("role", "is_staff", "is_active")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {
            "fields": ("first_name", "middle_name", "last_name", "email", "phone_number", "address", "gender", "date_of_birth", "profile_picture", "ssn")
        }),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Role", {"fields": ("role",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "password1", "password2", 
                "first_name", "middle_name", "last_name",
                "phone_number", "address", "gender", "date_of_birth", "profile_picture", 
                "role", "is_staff", "is_active", "ssn",
            )
        }),
    )

    search_fields = ("email", "username")
    ordering = ("email",)

admin.site.register(User, CustomUserAdmin)
