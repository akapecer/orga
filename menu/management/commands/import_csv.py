import csv
import os
from django.core.management.base import BaseCommand
from menu.models import Piatto, Categoria, Allergene

class Command(BaseCommand):
    help = 'Importa il menu da un file CSV. Formato: Categoria, Nome Piatto, Prezzo, Allergeni(es. "1,7")'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Il percorso del file CSV da caricare')

    def handle(self, *args, **options):
        csv_path = options['csv_file']

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'File non trovato: {csv_path}'))
            return

        # 1. Assicuriamoci che gli allergeni base esistano nel database
        # (Utile visto che il DB è nuovo)
        self.stdout.write("Verifica e creazione allergeni base...")
        for numero, nome in Allergene.ALLERGENE_CHOICES:
            obj, created = Allergene.objects.get_or_create(
                numero=numero,
                defaults={'nome': nome}
            )
            if created:
                self.stdout.write(f"- Creato allergene {numero}: {nome}")

        # 2. Leggiamo il file CSV
        # utf-8-sig gestisce automaticamente il BOM se il CSV è salvato da Excel
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Rileva automaticamente se il separatore è virgola o punto e virgola
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
            except csv.Error:
                dialect = 'excel' # Fallback
            
            reader = csv.reader(f, dialect)
            
            # Salta l'intestazione (la prima riga con i titoli)
            next(reader, None)

            count = 0
            self.stdout.write("Inizio importazione piatti...")

            for row_idx, row in enumerate(reader, start=2): # start=2 perché riga 1 è header
                if not row: continue # Salta righe vuote
                
                try:
                    # Mappatura colonne (modifica gli indici se il tuo CSV è diverso)
                    # Colonna 0: Categoria
                    # Colonna 1: Nome Piatto
                    # Colonna 2: Prezzo
                    # Colonna 3: Allergeni (numeri separati da virgola, es: "1, 3, 7")
                    
                    cat_nome = row[0].strip()
                    piatto_nome = row[1].strip()
                    
                    # Gestione prezzo (sostituisce virgola con punto per i decimali)
                    prezzo_str = row[2].strip().replace('€', '').replace(',', '.')
                    
                    # Gestione allergeni (opzionale)
                    allergeni_str = row[3].strip() if len(row) > 3 else ""

                    if not cat_nome or not piatto_nome:
                        self.stdout.write(self.style.WARNING(f"Riga {row_idx} saltata: Dati mancanti."))
                        continue

                    # Crea o recupera la Categoria
                    categoria, _ = Categoria.objects.get_or_create(nome=cat_nome)

                    # Crea o aggiorna il Piatto
                    piatto, created = Piatto.objects.update_or_create(
                        nome=piatto_nome,
                        defaults={
                            'prezzo': float(prezzo_str),
                            'categoria': categoria
                        }
                    )

                    # Collega gli allergeni
                    if allergeni_str:
                        # Pulisce la stringa e prende solo i numeri validi
                        numeri = []
                        for n in allergeni_str.replace('"', '').split(','): # Rimuove virgolette extra
                            n = n.strip()
                            if n.isdigit():
                                numeri.append(int(n))
                        
                        if numeri:
                            allergeni_objs = Allergene.objects.filter(numero__in=numeri)
                            piatto.allergeni.set(allergeni_objs)

                    action = "Creato" if created else "Aggiornato"
                    self.stdout.write(f"{action}: {piatto.nome} ({categoria.nome})")
                    count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Errore alla riga {row_idx} ({row}): {e}"))

            self.stdout.write(self.style.SUCCESS(f"Finito! {count} piatti importati correttamente."))