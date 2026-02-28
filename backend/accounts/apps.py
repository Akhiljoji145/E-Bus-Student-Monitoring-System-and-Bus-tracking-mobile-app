from django.apps import AppConfig
import sys

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # We only want to run the scheduler once, not in every worker or management command (like migrate)
        # Avoid running during 'manage.py' commands unless it's 'runserver'
        if 'runserver' in sys.argv or 'wsgi' in sys.argv[0] or 'gunicorn' in sys.argv[0]:
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except ImportError:
                pass
