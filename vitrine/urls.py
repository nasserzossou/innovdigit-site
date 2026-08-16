from django.urls import path
from . import views

urlpatterns = [
    path("", views.AccueilView.as_view(), name="accueil"),
    path("services/", views.ServicesView.as_view(), name="services"),
    path("projets-realises/", views.ProjetsRealisesView.as_view(), name="projets_realises"),
    path("temoignages/", views.TemoignagesView.as_view(), name="temoignages"),
    path("partenariat/", views.PartenariatView.as_view(), name="partenariat"),
    path("annonces/", views.AnnoncesView.as_view(), name="annonces"),
    path("a-propos/", views.AProposView.as_view(), name="a_propos"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("confiez-nous-projet/", views.ConfiezNousProjetView.as_view(), name="confiez_nous_projet"),
]
