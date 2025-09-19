from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    label = "users"  # Explicitly set the app label
    verbose_name = "User Management"
    
    def ready(self):
        # Import signals to register them
        try:
            import users.signals  # noqa
        except ImportError:
            pass  # Signals module is optional
