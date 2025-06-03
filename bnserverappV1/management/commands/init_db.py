from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from bnserverappV1.models import User

class Command(BaseCommand):
    help = 'Initializes the database with an admin user if none exists'

    def handle(self, *args, **options):
        # Check if any admin user exists
        if not User.objects.filter(role='admin').exists():
            # Create default admin user
            admin_user = User(
                username='admin',
                password=make_password('admin'),
                role='admin'
            )
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
        else:
            self.stdout.write(self.style.SUCCESS('Admin user already exists'))