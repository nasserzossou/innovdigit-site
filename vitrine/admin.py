from django.contrib import admin
from .models import (
    Projet, Attestation, Partenaire, Recrutement, ProjetEnCours,
    MessageContact, DemandePartenariat, DemandeProjet
)


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "etiquette_affichee", "actif", "ordre", "est_concept")
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
    )


@admin.register(Attestation)
class AttestationAdmin(admin.ModelAdmin):
    list_display = ("client_nom", "description", "actif", "ordre")
    list_editable = ("ordre", "actif")
    search_fields = ("client_nom", "description")
    ordering = ("ordre", "-date_creation")


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ("nom", "site_web", "actif", "ordre")
    list_editable = ("ordre", "actif")
    search_fields = ("nom",)
    ordering = ("ordre", "-date_creation")


@admin.register(Recrutement)
class RecrutementAdmin(admin.ModelAdmin):
    list_display = ("titre", "lieu", "type_contrat", "statut", "date_publication", "actif", "ordre")
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
    list_display = ("nom", "email", "sujet", "date_envoi", "traite")
    list_filter = ("sujet", "traite")
    list_editable = ("traite",)
    search_fields = ("nom", "email", "message")
    readonly_fields = ("nom", "email", "telephone", "sujet", "message", "date_envoi")
    ordering = ("-date_envoi",)

    def has_add_permission(self, request):
        # Les messages arrivent uniquement via le formulaire du site
        return False


@admin.register(DemandePartenariat)
class DemandePartenariatAdmin(admin.ModelAdmin):
    list_display = ("entreprise", "contact", "type_partenariat", "date_rdv", "date_envoi", "traite")
    list_filter = ("type_partenariat", "traite")
    list_editable = ("traite",)
    search_fields = ("entreprise", "contact", "email", "message")
    readonly_fields = (
        "entreprise", "contact", "email", "telephone", "type_partenariat",
        "date_rdv", "heure_rdv", "message", "date_envoi",
    )
    ordering = ("-date_envoi",)

    def has_add_permission(self, request):
        return False


@admin.register(DemandeProjet)
class DemandeProjetAdmin(admin.ModelAdmin):
    list_display = ("nom_entreprise", "nom_contact", "type_projet", "budget", "date_envoi", "traite")
    list_filter = ("type_projet", "budget", "traite")
    list_editable = ("traite",)
    search_fields = ("nom_entreprise", "nom_contact", "email", "description")
    readonly_fields = (
        "nom_entreprise", "nom_contact", "email", "telephone", "type_projet",
        "budget", "delai", "description", "date_envoi",
    )
    ordering = ("-date_envoi",)

    def has_add_permission(self, request):
        return False
