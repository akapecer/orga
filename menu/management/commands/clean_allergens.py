from django.core.management.base import BaseCommand
from menu.models import Allergene

class Command(BaseCommand):
    help = 'Rimuove gli allergeni che non hanno un numero valido.'

    def handle(self, *args, **kwargs):
        allergeni_senza_numero = Allergene.objects.filter(numero__isnull=True)

        if allergeni_senza_numero.exists():
            self.stdout.write(self.style.WARNING(f"Trovati {allergeni_senza_numero.count()} allergeni senza numero."))

            for allergene in allergeni_senza_numero:
                self.stdout.write(f"Rimuovo l'allergene: {allergene.nome} (id: {allergene.id})")
                allergene.delete()

            self.stdout.write(self.style.SUCCESS("Rimozione allergeni senza numero completata."))
        else:
            self.stdout.write(self.style.SUCCESS("Nessun allergene senza numero trovato."))
