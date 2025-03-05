from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = "Crea un superuser se non esiste già"

    def handle(self, *args, **kwargs):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "gugu_grotesque")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "cinelligrafica@gmail.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "poeta72")

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' creato con successo!"))
        else:
            self.stdout.write(self.style.WARNING(f"Il superuser '{username}' esiste già."))
