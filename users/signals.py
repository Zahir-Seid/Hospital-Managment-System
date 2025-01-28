from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .views import ROLE_TO_PROFILE_MAP  

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    #Signal to automatically create role-specific profiles when a new user is created.

    if created:
        # Fetch the profile model for the user's role
        role_data = ROLE_TO_PROFILE_MAP.get(instance.role)
        if role_data:
            profile_model = role_data[0]
            # Avoid duplicate profile creation
            profile_model.objects.get_or_create(user=instance)
