from django.contrib import messages
from django.views.generic import TemplateView, ListView, FormView
from .models import Projet, Attestation, Partenaire, Recrutement, ProjetEnCours
from .forms import MessageContactForm, DemandePartenariatForm, DemandeProjetForm


class PageBase(TemplateView):
    """Vue de base pour les pages statiques : ajoute page_actif au contexte
    à partir du nom de la vue (utilisé pour surligner le lien actif dans la nav)."""
    page_actif = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_actif"] = self.page_actif
        return ctx


class AccueilView(PageBase):
    template_name = "accueil.html"
    page_actif = "accueil"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["partenaires"] = Partenaire.objects.filter(actif=True)
        return ctx


class ServicesView(PageBase):
    template_name = "services.html"
    page_actif = "services"


class TemoignagesView(PageBase):
    template_name = "temoignages.html"
    page_actif = "temoignages"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["attestations"] = Attestation.objects.filter(actif=True)
        return ctx


class PartenariatView(FormView):
    template_name = "partenariat.html"
    form_class = DemandePartenariatForm
    page_actif = "partenariat"

    def get_success_url(self):
        return self.request.path + "?envoye=1"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_actif"] = self.page_actif
        ctx["partenaires"] = Partenaire.objects.filter(actif=True)
        ctx["message_envoye"] = self.request.GET.get("envoye") == "1"
        return ctx

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class AnnoncesView(PageBase):
    template_name = "annonces.html"
    page_actif = "annonces"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["recrutements"] = Recrutement.objects.filter(actif=True)
        ctx["projets_en_cours"] = ProjetEnCours.objects.filter(actif=True)
        return ctx


class AProposView(PageBase):
    template_name = "a_propos.html"
    page_actif = "a_propos"


class ContactView(FormView):
    template_name = "contact.html"
    form_class = MessageContactForm
    page_actif = "contact"

    def get_success_url(self):
        return self.request.path + "?envoye=1"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_actif"] = self.page_actif
        ctx["message_envoye"] = self.request.GET.get("envoye") == "1"
        return ctx

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ConfiezNousProjetView(FormView):
    template_name = "confiez_nous_projet.html"
    form_class = DemandeProjetForm
    page_actif = "confiez_nous_projet"

    def get_success_url(self):
        return self.request.path + "?envoye=1"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_actif"] = self.page_actif
        ctx["message_envoye"] = self.request.GET.get("envoye") == "1"
        return ctx

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ProjetsRealisesView(ListView):
    """Page dynamique : liste des projets réalisés, gérée depuis l'admin Django."""
    model = Projet
    template_name = "projets_realises.html"
    context_object_name = "projets"

    def get_queryset(self):
        return Projet.objects.filter(actif=True).order_by("ordre", "-date_creation")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_actif"] = "projets_realises"
        ctx["categories"] = Projet.CATEGORIE_CHOIX
        return ctx
