from django.urls import path
from . import api, views

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
    path("annonces/postuler/<int:pk>/", views.postuler, name="postuler"),
    path("candidatures/<int:pk>/cv/", views.cv_candidature, name="cv_candidature"),
    path("verifier/<path:jeton>/", views.verifier_badge, name="verifier_badge"),
    # API de synchronisation eSoft INNOV.DIGIT (voir README)
    path("api/esoft/publier/", api.publier, name="api_esoft_publier"),
    path("api/esoft/demandes/", api.demandes, name="api_esoft_demandes"),
    path("api/esoft/accuser/", api.accuser, name="api_esoft_accuser"),
]
