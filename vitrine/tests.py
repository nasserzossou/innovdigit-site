import base64
import hashlib
import io
import json
import os
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import (
    BadgePublic, Candidature, Coordonnees, DemandePartenariat, DemandeProjet, MessageContact,
    Partenaire, Projet, ProjetEnCours, Recrutement,
)

JETON = "jeton-de-test-" + "x" * 40
MEDIA_TEMP = tempfile.mkdtemp(prefix="innovdigit-tests-")
STORAGES_TEST = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def image_png(couleur=(10, 80, 160)):
    tampon = io.BytesIO()
    Image.new("RGB", (8, 8), couleur).save(tampon, format="PNG")
    return tampon.getvalue()


def bloc_image(contenu, nom="logo.png"):
    return {"nom": nom, "empreinte": hashlib.sha256(contenu).hexdigest(),
            "base64": base64.b64encode(contenu).decode()}


PDF_MINI = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@override_settings(MEDIA_ROOT=MEDIA_TEMP, STORAGES=STORAGES_TEST)
class BaseTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMP, ignore_errors=True)

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"ESOFT_SYNC_TOKEN": JETON})
        patcher.start()
        self.addCleanup(patcher.stop)

    def appel(self, nom, donnees=None, methode="post", jeton=JETON):
        entetes = {"HTTP_AUTHORIZATION": f"Bearer {jeton}"} if jeton else {}
        url = reverse(nom)
        if methode == "get":
            return self.client.get(url, **entetes)
        return self.client.post(url, data=json.dumps(donnees or {}),
                                content_type="application/json", **entetes)

    def publier(self, donnees):
        return self.appel("api_esoft_publier", donnees)


def charge_complete():
    logo = image_png()
    return {
        "version": 1,
        "envoye_le": "2026-10-10T09:15:00+01:00",
        "partenaires": [
            {"ref": "PAR-12", "nom": "ECCAM", "site_web": "https://eccam.example", "ordre": 10,
             "logo": bloc_image(logo)},
            {"ref": "PAR-13", "nom": "IFAC", "site_web": "", "ordre": 20, "logo": None},
        ],
        "recrutements": [
            {"ref": "REC-2026-003", "titre": "Développeur(se) web", "lieu": "Niamey, Niger",
             "type_contrat": "temps_plein", "statut": "ouvert", "description": "Profil et missions",
             "date_limite": "2099-11-30", "ordre": 10},
        ],
        "projets": [
            {"ref": "REA-5", "titre": "Site ONG", "categorie": "vitrine", "etiquette": "Site vitrine",
             "contexte": "Besoin", "objectif_atteint": "Livré", "ordre": 10,
             "image": bloc_image(image_png((200, 30, 30)), "rea5.png")},
        ],
        "badges": [
            {"empreinte": "a" * 64, "prenom": "Awa", "nom": "ALPHA", "poste": "Technicienne",
             "division": "Services IT", "matricule": "EMP-003", "statut": "valide"},
        ],
    }


class AuthentificationApiTests(BaseTest):
    def test_jeton_absent_dans_l_environnement_503(self):
        with mock.patch.dict(os.environ, {"ESOFT_SYNC_TOKEN": ""}):
            self.assertEqual(self.publier({}).status_code, 503)
            self.assertEqual(self.appel("api_esoft_demandes", methode="get").status_code, 503)

    def test_jeton_faux_401(self):
        r = self.appel("api_esoft_publier", {}, jeton="mauvais-jeton-" + "y" * 40)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.appel("api_esoft_demandes", methode="get", jeton=None).status_code, 401)

    def test_methode_interdite(self):
        r = self.client.get(reverse("api_esoft_publier"), HTTP_AUTHORIZATION=f"Bearer {JETON}")
        self.assertEqual(r.status_code, 405)

    def test_json_invalide_400(self):
        r = self.client.post(reverse("api_esoft_publier"), data="pas du json",
                             content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {JETON}")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])


class PublicationTests(BaseTest):
    def test_creation_puis_idempotence(self):
        r = self.publier(charge_complete())
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json(), {"ok": True, "partenaires": 2, "recrutements": 1,
                                    "projets": 1, "projets_en_cours": 0, "badges": 1,
                                    "coordonnees": False, "retires": 0})
        p = Partenaire.objects.get(ref_esoft="PAR-12")
        self.assertTrue(p.logo and os.path.exists(p.logo.path))
        nom_logo = p.logo.name
        self.assertEqual(Recrutement.objects.get(ref_esoft="REC-2026-003").date_limite.isoformat(), "2099-11-30")

        r2 = self.publier(charge_complete())
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(Partenaire.objects.count(), 2)
        self.assertEqual(Recrutement.objects.count(), 1)
        self.assertEqual(Projet.objects.count(), 1)
        self.assertEqual(BadgePublic.objects.count(), 1)
        p.refresh_from_db()
        self.assertEqual(p.logo.name, nom_logo)  # fichier non réécrit
        fichiers = [f for f in os.listdir(os.path.dirname(p.logo.path)) if f.startswith("par-12")]
        self.assertEqual(len(fichiers), 1)  # pas de doublon sur le disque

    def test_mise_a_jour_et_retrait(self):
        self.publier(charge_complete())
        charge = charge_complete()
        charge["partenaires"] = [dict(charge["partenaires"][0], nom="ECCAM SA", ordre=5)]
        r = self.publier(charge).json()
        self.assertEqual(r["retires"], 1)
        p = Partenaire.objects.get(ref_esoft="PAR-12")
        self.assertEqual((p.nom, p.ordre, p.actif), ("ECCAM SA", 5, True))
        self.assertFalse(Partenaire.objects.get(ref_esoft="PAR-13").actif)
        # Réapparition → de nouveau visible
        self.publier(charge_complete())
        self.assertTrue(Partenaire.objects.get(ref_esoft="PAR-13").actif)

    def test_image_changee_reecrite(self):
        self.publier(charge_complete())
        ancien = Projet.objects.get(ref_esoft="REA-5").image.path
        charge = charge_complete()
        charge["projets"][0]["image"] = bloc_image(image_png((0, 200, 0)))
        self.publier(charge)
        projet = Projet.objects.get(ref_esoft="REA-5")
        self.assertNotEqual(projet.image.path, ancien)
        self.assertTrue(os.path.exists(projet.image.path))
        self.assertFalse(os.path.exists(ancien))

    def test_image_absente_du_disque_reecrite(self):
        self.publier(charge_complete())
        projet = Projet.objects.get(ref_esoft="REA-5")
        os.remove(projet.image.path)
        self.publier(charge_complete())
        projet.refresh_from_db()
        self.assertTrue(os.path.exists(projet.image.path))

    def test_cle_absente_categorie_non_touchee_liste_vide_retire(self):
        self.publier(charge_complete())
        r = self.publier({"version": 1, "badges": []}).json()
        self.assertEqual(r["retires"], 0)
        self.assertEqual(Partenaire.objects.filter(actif=True).count(), 2)
        self.assertEqual(BadgePublic.objects.count(), 0)
        r = self.publier({"version": 1, "partenaires": []}).json()
        self.assertEqual(r["retires"], 2)
        self.assertEqual(Partenaire.objects.filter(actif=True).count(), 0)
        self.assertTrue(Recrutement.objects.get(ref_esoft="REC-2026-003").actif)

    def test_elements_manuels_non_touches(self):
        manuel = Recrutement.objects.create(titre="Offre manuelle", description="…")
        partenaire = Partenaire.objects.create(nom="Manuel", logo="partenaires/manuel.png")
        self.publier(charge_complete())
        self.publier({"version": 1, "recrutements": [], "partenaires": []})
        manuel.refresh_from_db()
        partenaire.refresh_from_db()
        self.assertTrue(manuel.actif)
        self.assertIsNone(manuel.ref_esoft)
        self.assertEqual(partenaire.nom, "Manuel")
        self.assertTrue(partenaire.actif)

    def test_image_invalide_ignoree(self):
        charge = charge_complete()
        faux = b"ceci n'est pas une image" * 10
        charge["partenaires"][0]["logo"] = bloc_image(faux, "faux.png")
        charge["projets"][0]["image"] = {"nom": "x.png", "empreinte": "0" * 64,
                                         "base64": base64.b64encode(image_png()).decode()}
        r = self.publier(charge)
        self.assertEqual(r.status_code, 200)
        p = Partenaire.objects.get(ref_esoft="PAR-12")
        self.assertTrue(p.actif)
        self.assertFalse(p.logo)
        self.assertFalse(Projet.objects.get(ref_esoft="REA-5").image)

    def test_image_trop_lourde_ignoree(self):
        charge = charge_complete()
        charge["projets"][0]["image"] = {"nom": "x.png", "base64": base64.b64encode(b"\0" * (3 * 1024 * 1024 + 10)).decode()}
        self.assertEqual(self.publier(charge).status_code, 200)
        self.assertFalse(Projet.objects.get(ref_esoft="REA-5").image)

    def test_format_invalide_400_et_rien_ecrit(self):
        charge = charge_complete()
        charge["recrutements"][0]["type_contrat"] = "cdi-inconnu"
        r = self.publier(charge)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])
        self.assertEqual(Partenaire.objects.count(), 0)  # transaction annulée

    def test_corps_volumineux_accepte(self):
        # Au-delà de DATA_UPLOAD_MAX_MEMORY_SIZE (2,5 Mo) mais sous la limite du contrat (25 Mo).
        charge = charge_complete()
        charge["recrutements"][0]["description"] = "x" * (4 * 1024 * 1024)
        self.assertEqual(self.publier(charge).status_code, 200)

    def test_badges_remplaces(self):
        self.publier(charge_complete())
        self.publier({"version": 1, "badges": [
            {"empreinte": "b" * 64, "prenom": "Ali", "nom": "BETA", "statut": "revoque"},
            {"empreinte": "c" * 64, "prenom": "Zara", "nom": "GAMMA", "statut": "inactif"},
        ]})
        self.assertEqual(set(BadgePublic.objects.values_list("prenom", flat=True)), {"Ali", "Zara"})


class DemandesTests(BaseTest):
    def test_demandes_listees_puis_accusees(self):
        self.publier(charge_complete())
        offre = Recrutement.objects.get(ref_esoft="REC-2026-003")
        contact = MessageContact.objects.create(nom="Moussa", email="m@example.com", sujet="devis", message="Bonjour")
        partenariat = DemandePartenariat.objects.create(
            entreprise="SARL", contact="Ibrahim", email="i@example.com", telephone="90",
            type_partenariat="technique", date_rdv="2026-10-20", heure_rdv="matin", message="Proposition")
        projet = DemandeProjet.objects.create(
            nom_entreprise="ONG", nom_contact="Fati", email="f@example.com", telephone="91",
            type_projet="site-web", description="Un site")
        cand = Candidature.objects.create(
            recrutement=offre, nom="ISSA", prenom="Awa", email="a@example.com", telephone="92",
            diplome="Licence", experience_ans=2, message="Motivée",
            cv=SimpleUploadedFile("cv-test.pdf", PDF_MINI, content_type="application/pdf"))
        chemin_cv = cand.cv.path
        self.assertTrue(os.path.exists(chemin_cv))

        r = self.appel("api_esoft_demandes", methode="get")
        self.assertEqual(r.status_code, 200)
        demandes = r.json()["demandes"]
        self.assertEqual([d["type"] for d in demandes], ["contact", "partenariat", "projet", "candidature"])
        c = demandes[3]
        self.assertEqual(c["recrutement_ref"], "REC-2026-003")
        self.assertEqual(base64.b64decode(c["cv"]["base64"]), PDF_MINI)
        self.assertEqual(demandes[1]["date_rdv"], "2026-10-20")

        r = self.appel("api_esoft_accuser", {"recus": [
            {"type": "candidature", "id": cand.pk}, {"type": "contact", "id": contact.pk}]})
        self.assertEqual(r.json(), {"ok": True, "accuses": 2})
        cand.refresh_from_db()
        self.assertTrue(cand.transmis and cand.transmis_le)
        self.assertFalse(cand.cv)
        self.assertFalse(os.path.exists(chemin_cv))
        restantes = self.appel("api_esoft_demandes", methode="get").json()["demandes"]
        self.assertEqual({(d["type"], d["id"]) for d in restantes},
                         {("partenariat", partenariat.pk), ("projet", projet.pk)})

    def test_candidature_offre_manuelle_ref_null(self):
        offre = Recrutement.objects.create(titre="Manuelle", description="…")
        Candidature.objects.create(recrutement=offre, nom="A", prenom="B", email="b@example.com",
                                   telephone="1", diplome="BTS")
        d = self.appel("api_esoft_demandes", methode="get").json()["demandes"][0]
        self.assertIsNone(d["recrutement_ref"])
        self.assertIsNone(d["cv"])

    def test_accuser_type_inconnu_400(self):
        r = self.appel("api_esoft_accuser", {"recus": [{"type": "autre", "id": 1}]})
        self.assertEqual(r.status_code, 400)


class CandidaturePubliqueTests(BaseTest):
    def donnees(self, **extra):
        d = {"nom": "ISSA", "prenom": "Awa", "email": "awa@example.com", "telephone": "+227 90",
             "diplome": "Licence informatique", "experience_ans": "2", "message": "Motivée",
             "cv": SimpleUploadedFile("Mon CV.pdf", PDF_MINI, content_type="application/pdf")}
        d.update(extra)
        return d

    def test_bouton_postuler_et_date_limite_sur_annonces(self):
        offre = Recrutement.objects.create(titre="Dev", description="…",
                                           date_limite=timezone.localdate() + timedelta(days=5))
        fermee = Recrutement.objects.create(titre="Fermée", description="…", statut="ferme")
        r = self.client.get(reverse("annonces"))
        self.assertContains(r, reverse("postuler", args=[offre.pk]))
        self.assertNotContains(r, reverse("postuler", args=[fermee.pk]))
        self.assertContains(r, "Date limite")

    def test_candidature_acceptee(self):
        offre = Recrutement.objects.create(titre="Dev", description="…")
        url = reverse("postuler", args=[offre.pk])
        r = self.client.post(url, self.donnees())
        self.assertRedirects(r, url + "?envoye=1")
        cand = Candidature.objects.get()
        self.assertTrue(cand.cv.name.startswith("candidatures/cv-"))
        self.assertContains(self.client.get(url + "?envoye=1"), "a bien été envoyée")

    def test_candidature_refusee_si_offre_fermee_ou_date_depassee(self):
        fermee = Recrutement.objects.create(titre="Fermée", description="…", statut="ferme")
        r = self.client.post(reverse("postuler", args=[fermee.pk]), self.donnees())
        self.assertEqual(r.status_code, 403)
        expiree = Recrutement.objects.create(titre="Expirée", description="…",
                                             date_limite=timezone.localdate() - timedelta(days=1))
        r = self.client.post(reverse("postuler", args=[expiree.pk]), self.donnees())
        self.assertEqual(r.status_code, 403)
        self.assertContains(self.client.get(reverse("postuler", args=[expiree.pk])), "date limite")
        inactive = Recrutement.objects.create(titre="Masquée", description="…", actif=False)
        self.assertEqual(self.client.get(reverse("postuler", args=[inactive.pk])).status_code, 404)
        self.assertEqual(Candidature.objects.count(), 0)

    def test_cv_signature_invalide_refuse(self):
        offre = Recrutement.objects.create(titre="Dev", description="…")
        faux = SimpleUploadedFile("cv.pdf", b"MZ\x90\x00 executable", content_type="application/pdf")
        r = self.client.post(reverse("postuler", args=[offre.pk]), self.donnees(cv=faux))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Candidature.objects.count(), 0)
        mauvais = SimpleUploadedFile("cv.docx", b"PK\x03\x04", content_type="application/zip")
        self.client.post(reverse("postuler", args=[offre.pk]), self.donnees(cv=mauvais))
        self.assertEqual(Candidature.objects.count(), 0)

    def test_champ_piege_robot(self):
        offre = Recrutement.objects.create(titre="Dev", description="…")
        url = reverse("postuler", args=[offre.pk])
        r = self.client.post(url, self.donnees(site_internet="http://spam.example"))
        self.assertRedirects(r, url + "?envoye=1")
        self.assertEqual(Candidature.objects.count(), 0)

    def test_cv_non_servi_publiquement(self):
        offre = Recrutement.objects.create(titre="Dev", description="…")
        self.client.post(reverse("postuler", args=[offre.pk]), self.donnees())
        cand = Candidature.objects.get()
        self.assertEqual(self.client.get("/media/" + cand.cv.name).status_code, 404)
        self.assertEqual(self.client.get("/media/x/../" + cand.cv.name).status_code, 404)
        r = self.client.get(reverse("cv_candidature", args=[cand.pk]))
        self.assertEqual(r.status_code, 302)  # connexion admin exigée


class VerifierBadgeTests(BaseTest):
    def creer(self, jeton, statut):
        BadgePublic.objects.create(empreinte=hashlib.sha256(jeton.encode("utf-8")).hexdigest(),
                                   prenom="Awa", nom="Alpha", poste="Technicienne",
                                   division="Services IT", matricule="EMP-003", statut=statut)

    def test_badge_valide(self):
        jeton = "ESB1.abc/def.signature"
        self.creer(jeton, "valide")
        r = self.client.get(f"/verifier/{jeton}/")
        self.assertContains(r, "Badge valide")
        self.assertContains(r, "ALPHA")
        self.assertContains(r, "EMP-003")
        self.assertContains(r, '<meta name="robots" content="noindex')

    def test_badge_revoque(self):
        self.creer("ESB1.revoque", "revoque")
        r = self.client.get("/verifier/ESB1.revoque/")
        self.assertContains(r, "Badge non valide")
        self.assertNotContains(r, "EMP-003")
        self.assertNotContains(r, "Technicienne")

    def test_badge_inconnu(self):
        r = self.client.get("/verifier/ESB1.inconnu/")
        self.assertContains(r, "Badge inconnu")
        self.assertEqual(r["X-Robots-Tag"], "noindex, nofollow")


# ---------------------------------------------------------------------------
# Contrat version 2 : projets en développement et coordonnées
# ---------------------------------------------------------------------------

def charge_v2():
    donnees = charge_complete()
    donnees["version"] = 2
    donnees["projets_en_cours"] = [
        {"ref": "PRJ-2026-004", "titre": "Plateforme de gestion scolaire", "domaine": "Développement web",
         "livraison_estimee": "Décembre 2026", "statut": "en_cours",
         "description": "Inscriptions, notes et bulletins.", "ordre": 10},
        {"ref": "PRJ-2026-007", "titre": "Application de livraison", "domaine": "Application mobile",
         "livraison_estimee": "", "statut": "termine", "description": "Suivi des courses.", "ordre": 20},
    ]
    donnees["coordonnees"] = {
        "nom_entreprise": "INNOV-DIGIT", "slogan": "Solutions numériques et maintenance informatique",
        "adresse": "Quartier Plateau, rue PL-34", "ville": "Niamey",
        "telephones": ["+227 90 11 22 33", "+227 80 44 55 66"], "email": "contact@innovdigit.example",
        "whatsapp": "+227 90 11 22 33", "horaires": "Lun-Ven 8h-17h30, Sam 9h-13h",
        "facebook": "https://facebook.com/innovdigit", "linkedin": "javascript:alert(1)", "site": "",
    }
    return donnees


class ContratV2Tests(BaseTest):
    def test_projets_en_cours_et_coordonnees_publies_puis_idempotence(self):
        r = self.publier(charge_v2())
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["projets_en_cours"], 2)
        self.assertTrue(r.json()["coordonnees"])
        p = ProjetEnCours.objects.get(ref_esoft="PRJ-2026-004")
        self.assertTrue(p.actif)
        self.assertEqual((p.domaine, p.livraison_estimee, p.statut, p.ordre),
                         ("Développement web", "Décembre 2026", "en_cours", 10))
        self.assertEqual(ProjetEnCours.objects.get(ref_esoft="PRJ-2026-007").livraison_estimee, "à confirmer")
        c = Coordonnees.objects.get(pk=1)
        self.assertEqual(c.telephones, ["+227 90 11 22 33", "+227 80 44 55 66"])
        self.assertEqual(c.linkedin, "")  # adresse non http(s) refusée
        self.assertEqual(c.nom_affiche, "INNOV DIGIT")

        r2 = self.publier(charge_v2())
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["retires"], 0)
        self.assertEqual(ProjetEnCours.objects.count(), 2)
        self.assertEqual(Coordonnees.objects.count(), 1)

    def test_retrait_projet_en_cours_et_manuel_non_touche(self):
        manuel = ProjetEnCours.objects.create(titre="Saisi à la main", domaine="IA", description="x")
        self.publier(charge_v2())
        donnees = charge_v2()
        donnees["projets_en_cours"] = donnees["projets_en_cours"][:1]
        r = self.publier(donnees)
        self.assertEqual(r.json()["retires"], 1)
        self.assertFalse(ProjetEnCours.objects.get(ref_esoft="PRJ-2026-007").actif)
        manuel.refresh_from_db()
        self.assertTrue(manuel.actif)
        annonces = self.client.get(reverse("annonces")).content.decode()
        self.assertIn("Plateforme de gestion scolaire", annonces)
        self.assertNotIn("Application de livraison", annonces)
        self.assertIn("Saisi à la main", annonces)

    def test_cles_absentes_rien_touche(self):
        self.publier(charge_v2())
        r = self.publier({"version": 2, "partenaires": []})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ProjetEnCours.objects.filter(actif=True).count(), 2)
        self.assertEqual(Coordonnees.objects.get(pk=1).email, "contact@innovdigit.example")

    def test_version_1_toujours_acceptee_et_version_inconnue_refusee(self):
        self.assertEqual(self.publier({"version": 1, "projets": []}).status_code, 200)
        self.assertEqual(self.publier({"version": 3}).status_code, 400)

    def test_coordonnees_invalides_400_rien_ecrit(self):
        donnees = charge_v2()
        donnees["coordonnees"]["telephones"] = {"a": 1}
        self.assertEqual(self.publier(donnees).status_code, 400)
        self.assertFalse(Coordonnees.objects.exists())
        self.assertFalse(ProjetEnCours.objects.exists())

    def test_pages_affichent_les_coordonnees_publiees(self):
        self.publier(charge_v2())
        for nom in ("contact", "a_propos", "accueil"):
            html = self.client.get(reverse(nom)).content.decode()
            self.assertIn("+227 90 11 22 33", html, nom)
            self.assertIn("contact@innovdigit.example", html, nom)
            self.assertNotIn("innovdigitinfo@gmail.com", html, nom)
        contact = self.client.get(reverse("contact")).content.decode()
        self.assertIn("Quartier Plateau, rue PL-34, Niamey", contact)
        self.assertIn("Lun-Ven 8h-17h30", contact)
        self.assertIn("https://wa.me/22790112233", contact)

    def test_repli_sans_coordonnees_publiees(self):
        self.assertFalse(Coordonnees.objects.exists())
        for nom in ("contact", "a_propos", "accueil", "annonces"):
            html = self.client.get(reverse(nom)).content.decode()
            self.assertIn("innovdigitinfo@gmail.com", html, nom)
            self.assertIn("+227 97 42 02 07", html, nom)
            self.assertIn("Niamey, Niger", html, nom)
        self.assertFalse(Coordonnees.objects.exists())  # l'affichage ne crée pas de ligne

    def test_champ_essentiel_vide_repli(self):
        donnees = charge_v2()
        donnees["coordonnees"].update({"email": "pas-un-email", "telephones": [], "adresse": ""})
        self.publier(donnees)
        html = self.client.get(reverse("contact")).content.decode()
        self.assertIn("innovdigitinfo@gmail.com", html)
        self.assertIn("+227 97 42 02 07", html)


class NomAfficheTests(BaseTest):
    def test_nom_sans_tiret_sur_toutes_les_pages(self):
        for nom in ("accueil", "services", "projets_realises", "temoignages", "partenariat", "annonces",
                    "a_propos", "contact", "confiez_nous_projet"):
            html = self.client.get(reverse(nom)).content.decode()
            self.assertIn("INNOV DIGIT", html, nom)
            self.assertNotIn("INNOV-DIGIT", html, nom)
            self.assertNotIn("INNOV_DIGIT", html, nom)
