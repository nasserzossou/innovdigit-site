"""Coordonnées de l'entreprise disponibles dans tous les gabarits (pied de page, Contact, À propos).

Elles viennent d'eSoft INNOV.DIGIT (clé « coordonnees » de la publication) ; tant que rien n'a été publié,
les valeurs de repli (COORDONNEES_REPLI) s'affichent."""
from django.db import DatabaseError

from .models import Coordonnees


def coordonnees(request):
    try:
        coord = Coordonnees.actuelles()
    except DatabaseError:  # base pas encore migrée : on affiche le repli
        coord = Coordonnees(pk=1)
    return {"coord": coord}
