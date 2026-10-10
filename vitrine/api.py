"""
API de synchronisation avec eSoft INNOV.DIGIT (plateforme interne).

C'est TOUJOURS la plateforme qui appelle le site (le site n'appelle jamais la plateforme) :

- POST api/esoft/publier/  : eSoft envoie tout l'état publié (partenaires, offres, réalisations, badges) ;
- GET  api/esoft/demandes/ : eSoft récupère les demandes reçues sur le site et pas encore transmises ;
- POST api/esoft/accuser/  : eSoft confirme la réception ; les CV transmis sont supprimés du site.

Authentification : en-tête « Authorization: Bearer <jeton> », comparé en temps constant à la
variable d'environnement ESOFT_SYNC_TOKEN. Sans cette variable, l'API est désactivée (503).
"""
import base64
import binascii
import hashlib
import hmac
import io
import json
import os
import re
from datetime import date
from functools import wraps

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from PIL import Image

from .models import (
    BadgePublic, Candidature, DemandePartenariat, DemandeProjet, MessageContact,
    Partenaire, Projet, Recrutement,
)

TAILLE_MAX_REQUETE = 25 * 1024 * 1024   # 25 Mo (contrat)
TAILLE_MAX_IMAGE = 3 * 1024 * 1024      # 3 Mo décodés (contrat)
LONGUEUR_MIN_JETON = 32
MAX_DEMANDES = 200
FORMATS_IMAGE = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}
RE_EMPREINTE = re.compile(r"^[0-9a-f]{64}$")


class ErreurFormat(Exception):
    """Contenu JSON non conforme au contrat → réponse 400."""


# ---------------------------------------------------------------------------
# Authentification et lecture du corps
# ---------------------------------------------------------------------------

def _jeton_configure():
    jeton = os.environ.get("ESOFT_SYNC_TOKEN", "").strip()
    return jeton if len(jeton) >= LONGUEUR_MIN_JETON else ""


def protege_par_jeton(vue):
    """503 si ESOFT_SYNC_TOKEN absent (ou trop court), 401 si le jeton reçu est faux."""

    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        attendu = _jeton_configure()
        if not attendu:
            return JsonResponse(
                {"ok": False, "erreur": "API de synchronisation désactivée (ESOFT_SYNC_TOKEN absent)."},
                status=503,
            )
        entete = request.headers.get("Authorization", "")
        recu = entete[7:].strip() if entete[:7].lower() == "bearer " else ""
        if not recu or not hmac.compare_digest(recu.encode("utf-8"), attendu.encode("utf-8")):
            return JsonResponse({"ok": False, "erreur": "Jeton invalide."}, status=401)
        return vue(request, *args, **kwargs)

    return enveloppe


def _lire_json(request):
    """Lit le corps (25 Mo max) sans passer par DATA_UPLOAD_MAX_MEMORY_SIZE (2,5 Mo par défaut)."""
    try:
        longueur = int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        longueur = 0
    if longueur > TAILLE_MAX_REQUETE:
        raise ErreurFormat("Requête trop volumineuse (25 Mo maximum).")
    brut = request.read(TAILLE_MAX_REQUETE + 1)
    if len(brut) > TAILLE_MAX_REQUETE:
        raise ErreurFormat("Requête trop volumineuse (25 Mo maximum).")
    try:
        donnees = json.loads(brut.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ErreurFormat("Corps JSON UTF-8 invalide.")
    if not isinstance(donnees, dict):
        raise ErreurFormat("Le corps doit être un objet JSON.")
    return donnees


def _erreur(message, status=400):
    return JsonResponse({"ok": False, "erreur": message}, status=status)


# ---------------------------------------------------------------------------
# Petits contrôles de format
# ---------------------------------------------------------------------------

def _texte(element, cle, max_len=None, obligatoire=False, defaut=""):
    valeur = element.get(cle, defaut)
    if valeur is None:
        valeur = ""
    if not isinstance(valeur, (str, int, float)) or isinstance(valeur, bool):
        raise ErreurFormat(f"Champ « {cle} » : texte attendu.")
    valeur = str(valeur).strip()
    if obligatoire and not valeur:
        raise ErreurFormat(f"Champ « {cle} » obligatoire.")
    if max_len:
        valeur = valeur[:max_len]
    return valeur


def _choix(element, cle, choix, defaut=None):
    valeur = element.get(cle) or defaut
    valides = {c[0] for c in choix}
    if valeur not in valides:
        raise ErreurFormat(f"Champ « {cle} » : valeur « {valeur} » non reconnue.")
    return valeur


def _ordre(element):
    valeur = element.get("ordre", 0)
    if valeur is None:
        return 0
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 0:
        raise ErreurFormat("Champ « ordre » : entier positif attendu.")
    return valeur


def _date(element, cle):
    valeur = element.get(cle)
    if valeur in (None, ""):
        return None
    try:
        return date.fromisoformat(str(valeur))
    except ValueError:
        raise ErreurFormat(f"Champ « {cle} » : date AAAA-MM-JJ attendue.")


def _liste(donnees, cle):
    """Renvoie la liste reçue, ou None si la clé est absente (catégorie non touchée)."""
    if cle not in donnees:
        return None
    liste = donnees[cle]
    if not isinstance(liste, list) or not all(isinstance(e, dict) for e in liste):
        raise ErreurFormat(f"« {cle} » doit être une liste d'objets.")
    return liste


def _refs(liste, cle):
    refs = []
    for element in liste:
        ref = _texte(element, "ref", obligatoire=True)
        if len(ref) > 40:
            raise ErreurFormat(f"{cle} : référence trop longue (« {ref[:50]} »).")
        refs.append(ref)
    if len(set(refs)) != len(refs):
        raise ErreurFormat(f"{cle} : références en double.")
    return refs


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def _decoder_image(image):
    """Renvoie (contenu, extension, empreinte) si l'image est un vrai PNG/JPEG/WEBP de 3 Mo max,
    sinon None (l'image est alors ignorée)."""
    b64 = image.get("base64")
    if not isinstance(b64, str) or not b64:
        return None
    if len(b64) > (TAILLE_MAX_IMAGE * 4) // 3 + 16:
        return None
    try:
        contenu = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not contenu or len(contenu) > TAILLE_MAX_IMAGE:
        return None
    empreinte = hashlib.sha256(contenu).hexdigest()
    annoncee = image.get("empreinte")
    if annoncee and str(annoncee).lower() != empreinte:
        return None
    try:
        with Image.open(io.BytesIO(contenu)) as img:
            format_reel = img.format
            img.verify()
    except Exception:
        return None
    extension = FORMATS_IMAGE.get(format_reel)
    if not extension:
        return None
    return contenu, extension, empreinte


def _supprimer_fichier(champ):
    if champ and champ.name:
        try:
            champ.storage.delete(champ.name)
        except Exception:
            pass


def _appliquer_image(objet, nom_champ, image):
    """Écrit l'image seulement si le fichier manque sur le disque ou si l'empreinte a changé.
    Image null ou invalide → l'élément reste publié sans image."""
    champ = getattr(objet, nom_champ)
    if image is not None and not isinstance(image, dict):
        raise ErreurFormat(f"Champ « {nom_champ} » : objet ou null attendu.")

    if image:
        annoncee = str(image.get("empreinte") or "").lower()
        if (annoncee and annoncee == objet.image_empreinte and champ.name
                and champ.storage.exists(champ.name)):
            return  # déjà à jour : rien à écrire
        decodee = _decoder_image(image)
        if decodee:
            contenu, extension, empreinte = decodee
            if (empreinte == objet.image_empreinte and champ.name
                    and champ.storage.exists(champ.name)):
                return
            _supprimer_fichier(champ)
            nom = f"{slugify(objet.ref_esoft) or 'esoft'}-{empreinte[:10]}.{extension}"
            # Un fichier orphelin du même nom (base effacée, disque conservé) est remplacé.
            cible = champ.field.generate_filename(objet, nom)
            if champ.storage.exists(cible):
                champ.storage.delete(cible)
            champ.save(nom, ContentFile(contenu), save=False)
            objet.image_empreinte = empreinte
            return

    # Pas d'image (null) ou image refusée : publié sans image.
    _supprimer_fichier(champ)
    setattr(objet, nom_champ, "")
    objet.image_empreinte = ""


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def _synchroniser(modele, liste, cle, remplir):
    """Crée / met à jour selon ref_esoft, puis retire (actif=False) les éléments eSoft absents.
    Renvoie (nombre reçu, nombre retiré)."""
    refs = _refs(liste, cle)
    existants = {o.ref_esoft: o for o in modele.objects.filter(ref_esoft__in=refs)}
    for ref, element in zip(refs, liste):
        objet = existants.get(ref) or modele(ref_esoft=ref)
        remplir(objet, element)
        objet.actif = True
        objet.ordre = _ordre(element)
        objet.save()
    retires = (
        modele.objects.filter(ref_esoft__isnull=False, actif=True)
        .exclude(ref_esoft__in=refs)
        .update(actif=False)
    )
    return len(liste), retires


def _remplir_partenaire(objet, element):
    objet.nom = _texte(element, "nom", 150, obligatoire=True)
    site = _texte(element, "site_web", 200)
    if site and not site.lower().startswith(("http://", "https://")):
        site = ""
    objet.site_web = site
    _appliquer_image(objet, "logo", element.get("logo"))


def _remplir_recrutement(objet, element):
    objet.titre = _texte(element, "titre", 150, obligatoire=True)
    objet.lieu = _texte(element, "lieu", 100) or "Niamey, Niger"
    objet.type_contrat = _choix(element, "type_contrat", Recrutement.TYPE_CONTRAT_CHOIX, "temps_plein")
    objet.statut = _choix(element, "statut", Recrutement.STATUT_CHOIX, "ouvert")
    objet.description = _texte(element, "description")
    objet.date_limite = _date(element, "date_limite")


def _remplir_projet(objet, element):
    objet.titre = _texte(element, "titre", 150, obligatoire=True)
    objet.categorie = _choix(element, "categorie", Projet.CATEGORIE_CHOIX, "vitrine")
    objet.etiquette = _texte(element, "etiquette", 60)
    objet.contexte = _texte(element, "contexte")
    objet.objectif_atteint = _texte(element, "objectif_atteint")
    _appliquer_image(objet, "image", element.get("image"))


def _remplacer_badges(liste):
    badges, vues = [], set()
    statuts = {c[0] for c in BadgePublic.STATUT_CHOIX}
    for element in liste:
        empreinte = _texte(element, "empreinte").lower()
        if not RE_EMPREINTE.match(empreinte):
            raise ErreurFormat("badges : empreinte SHA-256 (64 caractères hexadécimaux) attendue.")
        if empreinte in vues:
            raise ErreurFormat("badges : empreintes en double.")
        vues.add(empreinte)
        statut = element.get("statut") or "valide"
        if statut not in statuts:
            raise ErreurFormat(f"badges : statut « {statut} » non reconnu.")
        badges.append(BadgePublic(
            empreinte=empreinte,
            prenom=_texte(element, "prenom", 100, obligatoire=True),
            nom=_texte(element, "nom", 100, obligatoire=True),
            poste=_texte(element, "poste", 150),
            division=_texte(element, "division", 150),
            matricule=_texte(element, "matricule", 40),
            statut=statut,
        ))
    BadgePublic.objects.all().delete()
    BadgePublic.objects.bulk_create(badges)
    return len(badges)


@csrf_exempt
@require_http_methods(["POST"])
@protege_par_jeton
def publier(request):
    try:
        donnees = _lire_json(request)
        version = donnees.get("version", 1)
        if version != 1:
            raise ErreurFormat(f"Version de contrat non prise en charge : {version}.")
        reponse = {"ok": True, "partenaires": 0, "recrutements": 0, "projets": 0, "badges": 0, "retires": 0}
        categories = [
            ("partenaires", Partenaire, _remplir_partenaire),
            ("recrutements", Recrutement, _remplir_recrutement),
            ("projets", Projet, _remplir_projet),
        ]
        listes = {cle: _liste(donnees, cle) for cle, _, _ in categories}
        badges = _liste(donnees, "badges")
        with transaction.atomic():
            for cle, modele, remplir in categories:
                if listes[cle] is not None:
                    n, retires = _synchroniser(modele, listes[cle], cle, remplir)
                    reponse[cle] = n
                    reponse["retires"] += retires
            if badges is not None:
                reponse["badges"] = _remplacer_badges(badges)
    except ErreurFormat as exc:
        return _erreur(str(exc))
    return JsonResponse(reponse)


# ---------------------------------------------------------------------------
# Demandes reçues sur le site
# ---------------------------------------------------------------------------

def _iso(dt):
    return timezone.localtime(dt).isoformat() if dt else None


def _cv(candidature):
    if not candidature.cv or not candidature.cv.name:
        return None
    try:
        with candidature.cv.open("rb") as f:
            contenu = f.read()
    except (FileNotFoundError, OSError):
        return None
    return {
        "nom": os.path.basename(candidature.cv.name),
        "base64": base64.b64encode(contenu).decode("ascii"),
    }


def _demande_contact(m):
    return {"type": "contact", "id": m.pk, "recu_le": _iso(m.date_envoi), "nom": m.nom,
            "email": m.email, "telephone": m.telephone, "sujet": m.sujet, "message": m.message}


def _demande_partenariat(d):
    return {"type": "partenariat", "id": d.pk, "recu_le": _iso(d.date_envoi),
            "entreprise": d.entreprise, "contact": d.contact, "email": d.email,
            "telephone": d.telephone, "type_partenariat": d.type_partenariat,
            "date_rdv": d.date_rdv.isoformat() if d.date_rdv else None,
            "heure_rdv": d.heure_rdv, "message": d.message}


def _demande_projet(d):
    return {"type": "projet", "id": d.pk, "recu_le": _iso(d.date_envoi),
            "nom_entreprise": d.nom_entreprise, "nom_contact": d.nom_contact, "email": d.email,
            "telephone": d.telephone, "type_projet": d.type_projet, "budget": d.budget,
            "delai": d.delai, "description": d.description}


def _demande_candidature(c):
    return {"type": "candidature", "id": c.pk, "recu_le": _iso(c.recu_le),
            "recrutement_ref": c.recrutement.ref_esoft, "recrutement_titre": c.recrutement.titre,
            "nom": c.nom, "prenom": c.prenom, "email": c.email, "telephone": c.telephone,
            "diplome": c.diplome, "experience_ans": c.experience_ans, "message": c.message,
            "cv": _cv(c)}


# type → (modèle, champ date de réception, sérialiseur)
TYPES_DEMANDES = {
    "contact": (MessageContact, "date_envoi", _demande_contact),
    "partenariat": (DemandePartenariat, "date_envoi", _demande_partenariat),
    "projet": (DemandeProjet, "date_envoi", _demande_projet),
    "candidature": (Candidature, "recu_le", _demande_candidature),
}


@csrf_exempt
@require_http_methods(["GET"])
@protege_par_jeton
def demandes(request):
    candidats = []
    for type_demande, (modele, champ_date, serialiser) in TYPES_DEMANDES.items():
        qs = modele.objects.filter(transmis=False).order_by(champ_date, "pk")
        if modele is Candidature:
            qs = qs.select_related("recrutement")
        for objet in qs[:MAX_DEMANDES]:
            candidats.append((getattr(objet, champ_date), type_demande, objet.pk, objet, serialiser))
    candidats.sort(key=lambda c: (c[0], c[1], c[2]))
    resultat = [serialiser(objet) for _, _, _, objet, serialiser in candidats[:MAX_DEMANDES]]
    return JsonResponse({"demandes": resultat}, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
@require_http_methods(["POST"])
@protege_par_jeton
def accuser(request):
    try:
        donnees = _lire_json(request)
        recus = donnees.get("recus")
        if not isinstance(recus, list):
            raise ErreurFormat("« recus » doit être une liste.")
        par_type = {}
        for element in recus:
            if not isinstance(element, dict):
                raise ErreurFormat("« recus » doit contenir des objets {type, id}.")
            type_demande, ident = element.get("type"), element.get("id")
            if type_demande not in TYPES_DEMANDES:
                raise ErreurFormat(f"Type de demande inconnu : « {type_demande} ».")
            if isinstance(ident, bool) or not isinstance(ident, int):
                raise ErreurFormat("Identifiant entier attendu.")
            par_type.setdefault(type_demande, set()).add(ident)
    except ErreurFormat as exc:
        return _erreur(str(exc))

    maintenant = timezone.now()
    accuses = 0
    with transaction.atomic():
        for type_demande, ids in par_type.items():
            modele = TYPES_DEMANDES[type_demande][0]
            if modele is Candidature:
                # Les données personnelles (CV) ne restent pas sur le site.
                for candidature in Candidature.objects.filter(pk__in=ids):
                    if candidature.cv:
                        candidature.cv.delete(save=False)
                    candidature.transmis = True
                    candidature.transmis_le = candidature.transmis_le or maintenant
                    candidature.save(update_fields=["cv", "transmis", "transmis_le"])
                    accuses += 1
            else:
                accuses += modele.objects.filter(pk__in=ids).count()
                modele.objects.filter(pk__in=ids, transmis=False).update(
                    transmis=True, transmis_le=maintenant
                )
    return JsonResponse({"ok": True, "accuses": accuses})
