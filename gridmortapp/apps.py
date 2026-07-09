from django.apps import AppConfig


class GridmortappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gridmortapp'

    def ready(self):
        # Import signals to register them
        import gridmortapp.system_models.signals
