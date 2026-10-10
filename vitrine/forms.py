import os
import secrets

from django import forms
from .models import MessageContact, DemandePartenariat, DemandeProjet, Candidature


class MessageContactForm(forms.ModelForm):
    class Meta:
        model = MessageContact
        fields = ["nom", "email", "telephone", "sujet", "message"]


class DemandePartenariatForm(forms.ModelForm):
    class Meta:
        model = DemandePartenariat
        fields = [
            "entreprise", "contact", "email", "telephone",
            "type_partenariat", "date_rdv", "heure_rdv", "message",
        ]
        widgets = {
            "date_rdv": forms.DateInput(attrs={"type": "date", "id": "date-rdv"}),
        }


class DemandeProjetForm(forms.ModelForm):
    class Meta:
        model = DemandeProjet
        fields = [
            "nom_entreprise", "nom_contact", "email", "telephone",
            "type_projet", "budget", "delai", "description",
        ]


class CandidatureForm(forms.ModelForm):
    """Formulaire « Postuler » d'une offre de recrutement."""

    # Champ piège anti-robot : caché aux humains, les robots le remplissent.
    site_internet = forms.CharField(required=False, label="Ne pas remplir")

    class Meta:
        model = Candidature
        fields = [
            "nom", "prenom", "email", "telephone", "diplome",
            "experience_ans", "message", "cv",
        ]
        widgets = {
            "experience_ans": forms.NumberInput(attrs={"min": 0, "max": 60}),
            "message": forms.Textarea(attrs={"rows": 5}),
            "cv": forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cv"].required = True
        self.fields["site_internet"].widget.attrs.update(
            {"tabindex": "-1", "autocomplete": "off"}
        )

    def est_robot(self):
        return bool(self.data.get("site_internet"))

    def clean_experience_ans(self):
        valeur = self.cleaned_data.get("experience_ans")
        if valeur is not None and valeur > 60:
            raise forms.ValidationError("Valeur invalide.")
        return valeur

    def clean_cv(self):
        fichier = self.cleaned_data.get("cv")
        if fichier and hasattr(fichier, "name"):
            # Nom aléatoire : le nom d'origine (souvent « CV Prénom Nom ») n'est pas conservé.
            extension = os.path.splitext(fichier.name)[1].lower()
            fichier.name = f"cv-{secrets.token_hex(8)}{extension}"
        return fichier
