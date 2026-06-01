# history/apps.py
from django.apps import AppConfig


class HistoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'history'

    def ready(self):
        # 确保这行没有被注释
        import history.signals