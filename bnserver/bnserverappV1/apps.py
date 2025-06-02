from django.apps import AppConfig
import os
from django.core.management import call_command


class Bnserverappv1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bnserverappV1'

    def ready(self):
        # Only run in production or when explicitly requested
        if os.environ.get('RUN_MAIN', None) != 'true':
            try:
                # Run migrations
                call_command('migrate')
                # Initialize database with admin user
                call_command('init_db')
            except Exception as e:
                print(f"Error during database initialization: {str(e)}")
