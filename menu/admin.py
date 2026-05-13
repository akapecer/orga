from django.contrib import admin, messages
from .models import Categoria, Allergene, Piatto, Menu
from django.utils.html import format_html
from django import forms
from django.forms import CheckboxSelectMultiple
from django.utils import formats
from django.urls import path, reverse
from django.shortcuts import render
from collections import defaultdict
from webpush import send_group_notification

admin.site.site_header = "Grotesque"
admin.site.site_title = "Il Tuo Titolo Menu"
admin.site.index_title = "Gestione Menu"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome')
    search_fields = ('nome',)


class AllergeneForm(forms.ModelForm):
    class Meta:
        model = Allergene
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['numero'].choices = [(num, num) for num, _ in Allergene.ALLERGENE_CHOICES]


@admin.register(Allergene)
class AllergeneAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'numero')
    search_fields = ('nome',)
    ordering = ('numero',)
    form = AllergeneForm


# Campo personalizzato per mostrare "Numero. Nome" nelle checkbox
class AllergeneChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.numero}. {obj.nome}"

class PiattoAdminForm(forms.ModelForm):
    prezzo = forms.CharField(
        label="Prezzo",
        widget=forms.TextInput(attrs={'placeholder': 'es. 12.50'})
    )
    allergeni = AllergeneChoiceField(
        queryset=Allergene.objects.all().order_by('numero'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Piatto
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['prezzo'].initial = f"{self.instance.prezzo:.2f} €"

    def clean_prezzo(self):
        prezzo_str = self.cleaned_data['prezzo']
        prezzo_str = prezzo_str.replace("€", "").strip()

        try:
            prezzo = float(prezzo_str)
            if prezzo < 0:
                raise forms.ValidationError("Il prezzo non può essere negativo.")
            return prezzo
        except ValueError:
            raise forms.ValidationError("Inserisci un prezzo valido.")

    def clean_nome(self):
        nome = self.cleaned_data['nome'].strip()
        # Verifica se esiste già un piatto con lo stesso nome (case-insensitive)
        qs = Piatto.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError(f"Esiste già un piatto con il nome '{nome}'.")
        return nome


@admin.register(Piatto)
class PiattoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'categoria', 'prezzo')
    list_filter = ('categoria',)
    search_fields = ('nome', 'categoria__nome')
    form = PiattoAdminForm

    class Media:
        css = {
            'all': ('menu/css/dashboard.css',)
        }
        js = ('menu/js/menu-admin.js',)


class MenuAdminForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ('piatti', 'note_interne')


def formatted_data_creazione(obj):
    """Formats the data_creazione in italian."""
    if not obj.data_creazione:
        return "-"
    return formats.date_format(obj.data_creazione, "d F Y")


formatted_data_creazione.short_description = 'Data creazione'


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('anteprima_menu_link', 'genera_pdf_link')
    filter_horizontal = ('piatti',)
    form = MenuAdminForm
    fieldsets = (
        ('Composizione', {
            'fields': ('piatti',),
            'classes': ('collapse', 'open'),
            'description': 'Seleziona i piatti dalla lista di sinistra per aggiungerli al menu.'
        }),
        ('Note', {
            'fields': ('note_interne',),
            'description': 'Inserisci qui eventuali note interne per lo staff.'
        }),
    )

    actions = ['delete_selected', 'delete_all_menus', 'invia_notifica_push']

    class Media:
        css = {
            'all': ('menu/css/dashboard.css',)
        }

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/preview/', self.admin_site.admin_view(self.preview_view), name='menu_menu_preview'),
        ]
        return custom_urls + urls

    @staticmethod
    def _is_mobile_request(request):
        user_agent = (request.META.get('HTTP_USER_AGENT') or '').lower()
        mobile_markers = ('mobile', 'android', 'iphone', 'ipad', 'ipod')
        return any(marker in user_agent for marker in mobile_markers)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == 'piatti':
            field.queryset = Piatto.objects.select_related('categoria').order_by('categoria__nome', 'nome')
            field.label_from_instance = lambda obj: f"{obj.nome} - {obj.prezzo} EUR"
            if self._is_mobile_request(request):
                # Fallback widget on mobile: more reliable than filter_horizontal.
                field.widget = forms.SelectMultiple(attrs={'size': 18})
        return field

    def preview_view(self, request, object_id):
        menu = self.get_object(request, object_id)
        
        # Recupera i piatti ordinati per nome
        piatti_del_menu = menu.piatti.select_related('categoria').prefetch_related('allergeni').order_by('nome')

        # Raggruppa i piatti per categoria
        piatti_per_categoria = defaultdict(list)
        for piatto in piatti_del_menu:
            cat_nome = piatto.categoria.nome if piatto.categoria else "Senza Categoria"
            piatti_per_categoria[cat_nome].append(piatto)

        # Definisce l'ordine desiderato (coerente con la logica del PDF in views.py)
        ordine_preferito = ["Antipasti", "Primi Piatti", "Secondi Piatti", "Dolci"]
        categorie_presenti = list(piatti_per_categoria.keys())
        
        # Costruisce l'ordine finale: prima le categorie preferite, poi le altre in ordine alfabetico
        ordine_finale = [cat for cat in ordine_preferito if cat in piatti_per_categoria]
        ordine_finale.extend(sorted(cat for cat in categorie_presenti if cat not in ordine_preferito))

        # Crea un dizionario ordinato per l'anteprima
        menu_organizzato = {cat: piatti_per_categoria[cat] for cat in ordine_finale}

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': f"Anteprima: {menu}",
            'menu_organizzato': menu_organizzato,
            'change_url': reverse('admin:menu_menu_change', args=[menu.pk]),
        }
        
        return render(request, 'admin/menu/menu/preview.html', context)

    def anteprima_menu_link(self, obj):
        url = reverse('admin:menu_menu_preview', args=[obj.pk])
        # Usa la funzione esistente per formattare la data come testo del link
        return format_html('<a href="{}">{}</a>', url, formatted_data_creazione(obj))
    anteprima_menu_link.short_description = 'Data creazione (Anteprima)'
    anteprima_menu_link.admin_order_field = 'data_creazione'

    def genera_pdf_link(self, obj):
        return format_html('<a href="/genera-pdf-menu/{}/" target="_blank">Genera PDF</a>', obj.id)
    genera_pdf_link.short_description = 'Genera PDF'

    def delete_selected(self, request, queryset):
        for menu in queryset:
            menu.delete()
        self.message_user(request, f"I menu selezionati sono stati eliminati con successo.", level=messages.SUCCESS)
    delete_selected.short_description = "Elimina i menu selezionati"

    def delete_all_menus(self, request, queryset):
        """
        Delete all the menus present in the db.
        """
        deleted_count, _ = Menu.objects.all().delete()
        self.message_user(request, f"Sono stati eliminati tutti i {deleted_count} menu.", level=messages.SUCCESS)
    delete_all_menus.short_description = "Elimina tutti i menu"

    def invia_notifica_push(self, request, queryset):
        """
        Azione manuale per inviare una notifica push per i menu selezionati.
        """
        try:
            for menu in queryset:
                payload = {
                    "head": "Promozione Menu",
                    "body": f"Ti sei perso il nostro menu '{menu.nome}'? Scoprilo ora!",
                    "icon": "/static/images/logo_pwa_192.png",
                    "url": "/app/"
                }
                send_group_notification(group_name="clienti", payload=payload, ttl=1000)
            self.message_user(request, f"Notifica push inviata con successo per {queryset.count()} menu.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Errore: {str(e)}. Crea il gruppo 'clienti' in Webpush Admin.", level=messages.ERROR)

    invia_notifica_push.short_description = "Invia notifica push ai clienti"
