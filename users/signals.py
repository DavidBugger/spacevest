"""
Signal handlers for the users app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import CustomUser


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Create an auth token when a new user is created.
    """
    if created and hasattr(settings, 'REST_FRAMEWORK') and \
       'rest_framework.authtoken' in settings.INSTALLED_APPS:
        from rest_framework.authtoken.models import Token
        Token.objects.create(user=instance)
