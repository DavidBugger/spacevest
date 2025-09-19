import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from .custom_user import CustomUser

class PasswordResetToken(models.Model):
    """Model to store password reset tokens for users."""
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Password reset token for {self.user.email}"

    @property
    def is_valid(self):
        """Check if the token is valid (not used and not expired)."""
        return not self.is_used and timezone.now() < self.expires_at

    def mark_as_used(self):
        """Mark the token as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])

    @classmethod
    def create_for_user(cls, user, ip_address=None, user_agent=None):
        """Create a new password reset token for the given user."""
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(
            minutes=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 60 * 24)  # Default: 24 hours
        )
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
