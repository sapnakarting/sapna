from django.apps import AppConfig


class FleetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fleet'

    def ready(self):
        """Import signals when the app is ready."""
        import fleet.signals
