import hashlib

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, ListView, FormView
from .models import (
    Projet, Attestation, Partenaire, Recrutement, ProjetEnCours, Candidature, BadgePublic,
)
from .forms import MessageContactForm, DemandePartenariatForm, DemandeProjetForm, CandidatureForm


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
        ctx["partenaires"] = Partenaire.objects.filter(actif=True).exclude(logo="")
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
        ctx["partenaires"] = Partenaire.objects.filter(actif=True).exclude(logo="")
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


def postuler(request, pk):
    """Page « Postuler » d'une offre de recrutement (onglet Recrutement de la page Annonces)."""
    offre = get_object_or_404(Recrutement, pk=pk, actif=True)
    envoye = request.GET.get("envoye") == "1"
    form = None

    if offre.accepte_candidatures and not envoye:
        if request.method == "POST":
            form = CandidatureForm(request.POST, request.FILES)
            if form.is_valid():
                if not form.est_robot():  # robot : on fait semblant d'accepter
                    candidature = form.save(commit=False)
                    candidature.recrutement = offre
                    candidature.save()
                return redirect(request.path + "?envoye=1")
        else:
            form = CandidatureForm()

    reponse = render(request, "postuler.html", {
        "page_actif": "annonces",
        "offre": offre,
        "form": form,
        "message_envoye": envoye,
    })
    if request.method == "POST" and not offre.accepte_candidatures:
        reponse.status_code = 403
    return reponse


@staff_member_required
def cv_candidature(request, pk):
    """CV d'une candidature, réservé à l'équipe (les CV ne sont pas servis publiquement)."""
    candidature = get_object_or_404(Candidature, pk=pk)
    if not candidature.cv:
        raise Http404("CV indisponible (déjà transmis à eSoft ou absent).")
    try:
        fichier = candidature.cv.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("Fichier CV introuvable sur le disque.")
    return FileResponse(fichier, as_attachment=True, filename=candidature.cv.name.rsplit("/", 1)[-1])


@never_cache
def verifier_badge(request, jeton):
    """Vérification publique d'un badge du personnel (QR code du badge)."""
    badge = None
    if len(jeton) <= 4096:
        empreinte = hashlib.sha256(jeton.encode("utf-8")).hexdigest()
        badge = BadgePublic.objects.filter(empreinte=empreinte).first()
    if badge is None:
        etat = "inconnu"
    elif badge.statut == "valide":
        etat = "valide"
    else:
        etat = "non_valide"
    reponse = render(request, "verifier.html", {
        "etat": etat,
        "badge": badge if etat == "valide" else None,
        "verifie_le": timezone.localtime(),
    })
    reponse["X-Robots-Tag"] = "noindex, nofollow"
    return reponse
