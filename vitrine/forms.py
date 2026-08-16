from django import forms
from .models import MessageContact, DemandePartenariat, DemandeProjet


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
