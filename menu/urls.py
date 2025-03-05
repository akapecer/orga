from django.urls import path
from django.shortcuts import redirect
from . import views

# Funzione per reindirizzare alla pagina di login
def redirect_to_login(request):
    return redirect("/admin/login/")

urlpatterns = [
    path("", redirect_to_login, name="home"),  # Reindirizza alla pagina di login
    path('genera-pdf-menu/<int:menu_id>/', views.genera_pdf_menu, name='genera_pdf_menu'),
]
