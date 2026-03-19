from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from menu.models import Menu
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate


def pwa_home(request):
    if request.user.is_authenticated:
        return redirect("/admin/")

    return render(request, "pwa_home.html")


def genera_pdf_menu(request, menu_id):
    # Retrieve the menu from the database
    menu = Menu.objects.get(pk=menu_id)
    piatti_del_menu = menu.piatti.select_related("categoria").prefetch_related("allergeni").order_by("categoria__nome", "nome")
    ordine_categorie_preferito = ["Antipasti", "Primi Piatti", "Secondi Piatti", "Dolci"]

    # Group dishes by category, handling names not present in the preferred order.
    piatti_per_categoria = defaultdict(list)
    for piatto in piatti_del_menu:
        if piatto.categoria:
            piatti_per_categoria[piatto.categoria.nome].append(piatto)

    categorie_presenti = list(piatti_per_categoria.keys())
    ordine_categorie = [cat for cat in ordine_categorie_preferito if cat in piatti_per_categoria]
    ordine_categorie.extend(sorted(cat for cat in categorie_presenti if cat not in ordine_categorie_preferito))

    # PDF creation
    response = HttpResponse(content_type="application/pdf")
    nome_file = f"menu_{menu.data_creazione.strftime('%Y-%m-%d')}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{nome_file}"'

    # --- Create a SimpleDocTemplate instead of canvas
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # --- Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    category_style = styles["Heading2"]
    dish_style = styles["Normal"]
    allergen_style = styles["Italic"]

    dish_style.alignment = TA_LEFT
    dish_style.spaceAfter = 0  # Remove space after dish name

    allergen_style.spaceBefore = 3  # Add space before allergen
    allergen_style.spaceAfter = 6  # Add space after allergen

    # Page title
    title_text = f"Menu del giorno {menu.data_creazione.strftime('%Y-%m-%d')}"
    title_paragraph = Paragraph(title_text, title_style)
    elements.append(title_paragraph)
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))  # Add some space

    for categoria_nome in ordine_categorie:
        # Title for each category
        category_paragraph = Paragraph(categoria_nome, category_style)
        elements.append(category_paragraph)

        # Loop through dishes for each category
        for piatto in piatti_per_categoria[categoria_nome]:
            # Dish name and price
            dish_text = f"{piatto.nome} - {piatto.prezzo} EUR"
            dish_paragraph = Paragraph(dish_text, dish_style)
            elements.append(dish_paragraph)

            # Allergeni
            allergeni_piatto = [str(a.numero) for a in piatto.allergeni.all()]
            if allergeni_piatto:
                allergeni_str = ", ".join(allergeni_piatto)
                allergen_text = f"Allergeni: {allergeni_str}"
                allergen_paragraph = Paragraph(allergen_text, allergen_style)
                elements.append(allergen_paragraph)
            else:
                allergen_paragraph = Paragraph("Allergeni: Nessuno", allergen_style)
                elements.append(allergen_paragraph)

    # Aggiunta Note a fine PDF
    if menu.note_interne:
        elements.append(Paragraph("<br/><br/>", styles["Normal"]))
        elements.append(Paragraph("<b>Note:</b>", styles["Normal"]))
        # Escape del testo per evitare errori XML e conversione dei newline
        elements.append(Paragraph(escape(menu.note_interne).replace("\n", "<br/>"), styles["Normal"]))

    # --- Build the PDF
    doc.build(elements)

    return response
