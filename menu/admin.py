from django.contrib import admin, messages
from .models import Categoria, Allergene, Piatto, Menu
from django.utils.html import format_html
from django import forms
from django.forms import CheckboxSelectMultiple
from django.utils import formats
from django.urls import path, reverse
from django.shortcuts import render
from collections import defaultdict

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

    actions = ['delete_selected', 'delete_all_menus']

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

    def preview_view(self, request, object_id):
        menu = self.get_object(request, object_id)
        
        piatti_del_menu = menu.piatti.select_related('categoria').prefetch_related('allergeni').order_by('categoria__nome', 'nome')

        menu_organizzato = defaultdict(list)
        for piatto in piatti_del_menu:
            menu_organizzato[piatto.categoria.nome].append(piatto)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': f"Anteprima: {menu}",
            'menu_organizzato': dict(menu_organizzato),
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
