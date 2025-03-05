from django.http import HttpResponse
from menu.models import Menu, Piatto, Categoria
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT

def genera_pdf_menu(request, menu_id):
    # Retrieve the menu from the database
    menu = Menu.objects.get(pk=menu_id)
    piatti_del_menu = menu.piatti.all().order_by('nome')
    ordine_categorie = ["Antipasti", "Primi Piatti", "Secondi Piatti", "Dolci"]

    # Group dishes by category
    piatti_per_categoria = {}
    for categoria in ordine_categorie:
        piatti_per_categoria[categoria] = []
    for piatto in piatti_del_menu:
        piatti_per_categoria[piatto.categoria.nome].append(piatto)

    # PDF creation
    response = HttpResponse(content_type='application/pdf')
    nome_file = f"menu_{menu.data_creazione.strftime('%Y-%m-%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{nome_file}"'

    # --- Create a SimpleDocTemplate instead of canvas
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # --- Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    category_style = styles['Heading2']
    dish_style = styles['Normal']
    allergen_style = styles['Italic']

    dish_style.alignment = TA_LEFT
    dish_style.spaceAfter = 0  # Remove space after dish name

    allergen_style.spaceBefore = 3  # Add space before allergen
    allergen_style.spaceAfter = 6 #Add space after allergen

    # Page title
    title_text = f"Menu del giorno {menu.data_creazione.strftime('%Y-%m-%d')}"
    title_paragraph = Paragraph(title_text, title_style)
    elements.append(title_paragraph)
    elements.append(Paragraph("<br/><br/>", styles["Normal"])) #add some space

    for categoria_nome in ordine_categorie:
        # Title for each category
        category_paragraph = Paragraph(categoria_nome, category_style)
        elements.append(category_paragraph)

        # Loop through dishes for each category
        for piatto in piatti_per_categoria[categoria_nome]:
            # Dish name and price
            dish_text = f"{piatto.nome} - {piatto.prezzo}€"
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

    # --- Build the PDF
    doc.build(elements)

    return response

