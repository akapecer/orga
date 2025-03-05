from django.db import models
from django.utils.translation import gettext_lazy as _

class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Categoria")
        verbose_name_plural = _("Categorie")

    def __str__(self):
        return self.nome

class Allergene(models.Model):
    ALLERGENE_CHOICES = [
        (1, 'Cereali contenenti glutine'),
        (2, 'Crostacei'),
        (3, 'Uova'),
        (4, 'Pesce'),
        (5, 'Arachidi'),
        (6, 'Soia'),
        (7, 'Latte'),
        (8, 'Frutta a guscio'),
        (9, 'Sedano'),
        (10, 'Senape'),
        (11, 'Semi di sesamo'),
        (12, 'Anidride solforosa e solfiti'),
        (13, 'Lupini'),
        (14, 'Molluschi'),
    ]
    
    numero = models.IntegerField(choices=ALLERGENE_CHOICES, unique=True)
    nome = models.CharField(max_length=255)

    class Meta:
        verbose_name = _("Allergene")
        verbose_name_plural = _("Allergeni")

    def __str__(self):
        return str(self.numero)

class Piatto(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    prezzo = models.DecimalField(max_digits=6, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="piatti", null=True)
    allergeni = models.ManyToManyField(Allergene, blank=True)

    class Meta:
        verbose_name = _("Piatto")
        verbose_name_plural = _("Piatti")

    def __str__(self):
        return f"{self.nome} ({self.categoria.nome})"

class Menu(models.Model):
    nome = models.CharField(max_length=255)
    data_creazione = models.DateField(auto_now_add=True)
    piatti = models.ManyToManyField(Piatto)

    class Meta:
        verbose_name = _("Menu")
        verbose_name_plural = _("Menu")

    def __str__(self):
        return f"{self.nome} ({self.data_creazione})"
