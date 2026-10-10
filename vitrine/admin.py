from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Projet, Attestation, Partenaire, Recrutement, ProjetEnCours,
    MessageContact, DemandePartenariat, DemandeProjet, Candidature, BadgePublic,
)

MESSAGE_GERE_ESOFT = (
    "Géré depuis eSoft : les modifications faites ici seront écrasées "
    "à la prochaine synchronisation."
)


class GereDepuisEsoftMixin:
    """Affiche ref_esoft en lecture seule et prévient que l'élément est piloté par eSoft."""

    @admin.display(description="Origine", ordering="ref_esoft")
    def origine(self, obj):
        return f"eSoft ({obj.ref_esoft})" if obj.ref_esoft else "Saisi à la main"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is not None and obj.ref_esoft and request.method == "GET":
            messages.warning(request, MESSAGE_GERE_ESOFT)
        return super().change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        if request.method == "GET" and self.model.objects.filter(ref_esoft__isnull=False).exists():
            messages.info(
                request,
                "Éléments d'origine « eSoft » — " + MESSAGE_GERE_ESOFT,
            )
        return super().changelist_view(request, extra_context)


@admin.register(Projet)
class ProjetAdmin(GereDepuisEsoftMixin, admin.ModelAdmin):
    list_display = ("titre", "categorie", "etiquette_affichee", "actif", "ordre", "est_concept", "origine")
    readonly_fields = ("ref_esoft", "image_empreinte")
    list_filter = ("categorie", "actif", "est_concept")
    search_fields = ("titre", "contexte", "objectif_atteint")
    list_editable = ("ordre", "actif")
    ordering = ("ordre", "-date_creation")

    fieldsets = (
        ("Informations générales", {
            "fields": ("titre", "categorie", "etiquette", "image", "est_concept")
        }),
        ("Contenu", {
            "fields": ("contexte", "objectif_atteint")
        }),
        ("Affichage", {
            "fields": ("actif", "ordre")
        }),
        ("Synchronisation eSoft", {
            "fields": ("ref_esoft", "image_empreinte"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Attestation)
class AttestationAdmin(admin.ModelAdmin):
    list_display = ("client_nom", "description", "actif", "ordre")
    list_editable = ("ordre", "actif")
    search_fields = ("client_nom", "description")
    ordering = ("ordre", "-date_creation")


@admin.register(Partenaire)
class PartenaireAdmin(GereDepuisEsoftMixin, admin.ModelAdmin):
    list_display = ("nom", "site_web", "actif", "ordre", "origine")
    readonly_fields = ("ref_esoft", "image_empreinte")
    list_editable = ("ordre", "actif")
    search_fields = ("nom",)
    ordering = ("ordre", "-date_creation")


@admin.register(Recrutement)
class RecrutementAdmin(GereDepuisEsoftMixin, admin.ModelAdmin):
    list_display = ("titre", "lieu", "type_contrat", "statut", "date_publication", "date_limite",
                    "actif", "ordre", "origine")
    readonly_fields = ("ref_esoft",)
    list_filter = ("statut", "type_contrat", "actif")
    list_editable = ("ordre", "actif")
    search_fields = ("titre", "description")
    ordering = ("ordre", "-date_publication")


@admin.register(ProjetEnCours)
class ProjetEnCoursAdmin(admin.ModelAdmin):
    list_display = ("titre", "domaine", "statut", "livraison_estimee", "actif", "ordre")
    list_filter = ("statut", "actif")
    list_editable = ("ordre", "actif")
    search_fields = ("titre", "description")
    ordering = ("ordre", "-date_creation")


@admin.register(MessageContact)
class MessageContactAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "sujet", "date_envoi", "traite", "transmis")
    list_filter = ("sujet", "traite", "transmis")
    list_editable = ("traite",)
    search_fields = ("nom", "email", "message")
    readonly_fields = ("nom", "email", "telephone", "sujet", "message", "date_envoi",
                       "transmis", "transmis_le")
    ordering = ("-date_envoi",)

    def has_add_permission(self, request):
        # Les messages arrivent uniquement via le formulaire du site
        return False


@admin.register(DemandePartenariat)
class DemandePartenariatAdmin(admin.ModelAdmin):
    list_display = ("entreprise", "contact", "type_partenariat", "date_rdv", "date_envoi", "traite", "transmis")
    list_filter = ("type_partenariat", "traite", "transmis")
    list_editable = ("traite",)
    search_fields = ("entreprise", "contact", "email", "message")
    readonly_fields = (
        "entreprise", "contact", "email", "telephone", "type_partenariat",
        "date_rdv", "heure_rdv", "message", "date_envoi", "transmis", "transmis_le",
    )
    ordering = ("-date_envoi",)

    def has_add_permission(self, request):
        return False


@admin.register(DemandeProjet)
class DemandeProjetAdmin(admin.ModelAdmin):
    list_display = ("nom_entreprise", "nom_contact", "type_projet", "budget", "date_envoi", "traite", "transmis")
    list_filter = ("type_projet", "budget", "traite", "transmis")
    list_editable = ("traite",)
    search_fields = ("nom_entreprise", "nom_contact", "email", "description")
    readonly_fields = (
        "nom_entreprise", "nom_contact", "email", "telephone", "type_projet",
        "budget", "delai", "description", "date_envoi", "transmis", "transmis_le",
    )
    ordering = ("-date_envoi",)

    def has_add_permission(self, request):
        return False


@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    """Lecture seule : les candidatures arrivent par le bouton « Postuler » et sont
    transmises à eSoft (le CV est alors supprimé du site)."""
    list_display = ("prenom", "nom", "recrutement", "email", "experience_ans", "recu_le", "transmis")
    list_filter = ("transmis", "recrutement")
    search_fields = ("nom", "prenom", "email", "diplome")
    ordering = ("-recu_le",)
    fields = (
        "recrutement", "nom", "prenom", "email", "telephone", "diplome", "experience_ans",
        "message", "lien_cv", "recu_le", "transmis", "transmis_le",
    )
    readonly_fields = fields

    @admin.display(description="CV")
    def lien_cv(self, obj):
        if not obj.cv:
            return "— (transmis à eSoft et supprimé du site)" if obj.transmis else "—"
        return format_html(
            '<a href="{}">Télécharger le CV</a>', reverse("cv_candidature", args=[obj.pk])
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BadgePublic)
class BadgePublicAdmin(admin.ModelAdmin):
    """Lecture seule : la table est remplacée à chaque synchronisation eSoft."""
    list_display = ("prenom", "nom", "poste", "division", "matricule", "statut", "recu_le")
    list_filter = ("statut", "division")
    search_fields = ("nom", "prenom", "matricule")
    readonly_fields = ("empreinte", "prenom", "nom", "poste", "division", "matricule", "statut", "recu_le")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
