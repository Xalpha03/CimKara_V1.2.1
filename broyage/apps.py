from django.apps import AppConfig


class BroyageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'broyage'
    
    def ready(self):
        import broyage.signals

