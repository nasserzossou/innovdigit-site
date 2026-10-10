import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# Champ commun : référence de l'élément dans eSoft INNOV.DIGIT (plateforme interne).
# Vide (NULL) pour les éléments saisis à la main dans l'admin du site.
def _champ_ref_esoft():
    return models.CharField(
        "Référence eSoft", max_length=40, unique=True, null=True, blank=True,
        editable=False,
        help_text="Renseignée automatiquement par la synchronisation eSoft.",
    )


class Projet(models.Model):
    """Un projet réalisé par INNOV-DIGIT, affiché sur la page 'Projets Réalisés'."""

    CATEGORIE_CHOIX = [
        ("vitrine", "Vitrine 5-10 Pages"),
        ("ecommerce", "E-Commerce"),
        ("onepage", "One Page"),
        ("refonte", "Refontes"),
        ("mobile", "Applications Mobiles"),
        ("communication", "Travaux de Communication"),
        ("autres", "Autres Projets"),
    ]

    titre = models.CharField("Titre du projet", max_length=150)
    categorie = models.CharField(
        "Catégorie", max_length=20, choices=CATEGORIE_CHOIX, default="vitrine"
    )
    etiquette = models.CharField(
        "Étiquette affichée",
        max_length=60,
        help_text="Texte affiché sur la carte (ex: 'Site Vitrine', 'Projet Social'). "
        "Laisser vide pour utiliser le nom de la catégorie.",
        blank=True,
    )
    contexte = models.TextField("Contexte", help_text="Le besoin du client au départ.")
    objectif_atteint = models.TextField(
        "Objectif atteint", help_text="Ce qu'INNOV-DIGIT a livré / résolu."
    )
    image = models.ImageField(
        "Image du projet", upload_to="projets/", blank=True, null=True
    )
    est_concept = models.BooleanField(
        "Projet concept (démo, pas un vrai client)",
        default=False,
        help_text="Affiche le badge 'Concept' sur la carte.",
    )
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre = models.PositiveIntegerField(
        "Ordre d'affichage", default=0,
        help_text="Les projets avec un chiffre plus petit apparaissent en premier."
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    ref_esoft = _champ_ref_esoft()
    image_empreinte = models.CharField(
        "Empreinte de l'image (SHA-256)", max_length=64, blank=True, editable=False
    )

    class Meta:
        verbose_name = "Projet réalisé"
        verbose_name_plural = "Projets réalisés"
        ordering = ["ordre", "-date_creation"]

    def __str__(self):
        return self.titre

    def etiquette_affichee(self):
        return self.etiquette or self.get_categorie_display()


class Attestation(models.Model):
    """Attestation de travail scannée, affichée sur la page Témoignages."""
    client_nom = models.CharField("Nom du client", max_length=150)
    description = models.CharField(
        "Description", max_length=150,
        help_text="Ex : 'Attestation de prestation - Site web'"
    )
    image = models.ImageField("Scan de l'attestation", upload_to="attestations/")
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre = models.PositiveIntegerField("Ordre d'affichage", default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Attestation"
        verbose_name_plural = "Attestations"
        ordering = ["ordre", "-date_creation"]

    def __str__(self):
        return f"{self.client_nom} — {self.description}"


class Partenaire(models.Model):
    """Logo affiché dans la section 'Ils nous font déjà confiance'."""
    nom = models.CharField("Nom du partenaire", max_length=150)
    logo = models.ImageField("Logo", upload_to="partenaires/")
    site_web = models.URLField("Site web", blank=True)
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre = models.PositiveIntegerField("Ordre d'affichage", default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    ref_esoft = _champ_ref_esoft()
    image_empreinte = models.CharField(
        "Empreinte du logo (SHA-256)", max_length=64, blank=True, editable=False
    )

    class Meta:
        verbose_name = "Partenaire"
        verbose_name_plural = "Partenaires"
        ordering = ["ordre", "-date_creation"]

    def __str__(self):
        return self.nom


class Recrutement(models.Model):
    """Offre d'emploi affichée dans l'onglet 'Recrutement' de la page Annonces."""

    TYPE_CONTRAT_CHOIX = [
        ("temps_plein", "Temps plein"),
        ("stage", "Stage"),
        ("temps_partiel", "Temps partiel"),
        ("freelance", "Freelance"),
    ]
    STATUT_CHOIX = [
        ("ouvert", "Poste ouvert"),
        ("ferme", "Poste fermé"),
    ]

    titre = models.CharField("Titre du poste", max_length=150)
    lieu = models.CharField("Lieu", max_length=100, default="Niamey, Niger")
    type_contrat = models.CharField(
        "Type de contrat", max_length=20, choices=TYPE_CONTRAT_CHOIX, default="temps_plein"
    )
    statut = models.CharField("Statut", max_length=10, choices=STATUT_CHOIX, default="ouvert")
    description = models.TextField("Description du poste")
    date_publication = models.DateField("Date de publication", auto_now_add=True)
    date_limite = models.DateField("Date limite de candidature", null=True, blank=True)
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre = models.PositiveIntegerField("Ordre d'affichage", default=0)
    ref_esoft = _champ_ref_esoft()

    class Meta:
        verbose_name = "Offre de recrutement"
        verbose_name_plural = "Offres de recrutement"
        ordering = ["ordre", "-date_publication"]

    def __str__(self):
        return self.titre

    @property
    def date_limite_depassee(self):
        return bool(self.date_limite and self.date_limite < timezone.localdate())

    @property
    def accepte_candidatures(self):
        """Vrai si l'offre est visible, ouverte et que la date limite n'est pas passée."""
        return self.actif and self.statut == "ouvert" and not self.date_limite_depassee


class ProjetEnCours(models.Model):
    """Projet en développement affiché dans l'onglet 'Projets en cours' de la page Annonces."""

    STATUT_CHOIX = [
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
    ]

    titre = models.CharField("Titre du projet", max_length=150)
    domaine = models.CharField(
        "Domaine", max_length=100,
        help_text="Ex : 'Développement web', 'Analyse de données', 'Application mobile'"
    )
    livraison_estimee = models.CharField(
        "Livraison estimée", max_length=100, default="à confirmer",
        help_text="Ex : 'Décembre 2026' ou 'à confirmer'"
    )
    statut = models.CharField("Statut", max_length=10, choices=STATUT_CHOIX, default="en_cours")
    description = models.TextField("Description du projet")
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre = models.PositiveIntegerField("Ordre d'affichage", default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Projet en cours"
        verbose_name_plural = "Projets en cours"
        ordering = ["ordre", "-date_creation"]

    def __str__(self):
        return self.titre


class MessageContact(models.Model):
    """Message envoyé via le formulaire de la page Contact."""

    SUJET_CHOIX = [
        ("devis", "Demande de devis"),
        ("information", "Demande d'information"),
        ("support", "Support technique"),
        ("partenariat", "Partenariat"),
        ("autre", "Autre"),
    ]

    nom = models.CharField("Nom complet", max_length=150)
    email = models.EmailField("Email")
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    sujet = models.CharField("Sujet", max_length=20, choices=SUJET_CHOIX)
    message = models.TextField("Message")
    date_envoi = models.DateTimeField("Reçu le", auto_now_add=True)
    traite = models.BooleanField("Traité", default=False)
    transmis = models.BooleanField("Transmis à eSoft", default=False, editable=False)
    transmis_le = models.DateTimeField("Transmis le", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ["-date_envoi"]

    def __str__(self):
        return f"{self.nom} — {self.get_sujet_display()} ({self.date_envoi:%d/%m/%Y})"


class DemandePartenariat(models.Model):
    """Demande envoyée via le formulaire de la page Partenariat."""

    TYPE_CHOIX = [
        ("technique", "Partenariat technique"),
        ("fournisseur", "Partenariat fournisseur"),
        ("institutionnel", "Partenariat institutionnel"),
        ("apporteur", "Apporteur d'affaires"),
        ("autre", "Autre"),
    ]
    HEURE_CHOIX = [
        ("", "-- Choisir --"),
        ("matin", "Matin (9h - 12h)"),
        ("apres-midi", "Après-midi (14h - 17h)"),
    ]

    entreprise = models.CharField("Nom de l'entreprise / organisation", max_length=150)
    contact = models.CharField("Nom du contact", max_length=150)
    email = models.EmailField("Email")
    telephone = models.CharField("Téléphone", max_length=30)
    type_partenariat = models.CharField("Type de partenariat", max_length=20, choices=TYPE_CHOIX)
    date_rdv = models.DateField("Date souhaitée pour le rendez-vous")
    heure_rdv = models.CharField("Heure préférée", max_length=15, choices=HEURE_CHOIX, blank=True)
    message = models.TextField("Proposition")
    date_envoi = models.DateTimeField("Reçu le", auto_now_add=True)
    traite = models.BooleanField("Traité", default=False)
    transmis = models.BooleanField("Transmis à eSoft", default=False, editable=False)
    transmis_le = models.DateTimeField("Transmis le", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Demande de partenariat"
        verbose_name_plural = "Demandes de partenariat"
        ordering = ["-date_envoi"]

    def __str__(self):
        return f"{self.entreprise} — {self.get_type_partenariat_display()} ({self.date_envoi:%d/%m/%Y})"


class DemandeProjet(models.Model):
    """Demande envoyée via le formulaire 'Confiez-nous votre projet'."""

    TYPE_PROJET_CHOIX = [
        ("site-web", "Site web"),
        ("application-gestion", "Application de gestion"),
        ("application-mobile", "Application mobile"),
        ("conception", "Conception graphique"),
        ("communication", "Communication"),
        ("materiel", "Achat de matériel informatique"),
        ("services-it", "Services IT / Maintenance"),
        ("autre", "Autre"),
    ]
    BUDGET_CHOIX = [
        ("", "-- Choisir --"),
        ("moins-500000", "Moins de 500 000"),
        ("500000-2000000", "500 000 - 2 000 000"),
        ("2000000-5000000", "2 000 000 - 5 000 000"),
        ("plus-5000000", "Plus de 5 000 000"),
        ("a-discuter", "À discuter"),
    ]
    DELAI_CHOIX = [
        ("", "-- Choisir --"),
        ("urgent", "Urgent (moins d'1 mois)"),
        ("1-3-mois", "1 à 3 mois"),
        ("3-6-mois", "3 à 6 mois"),
        ("flexible", "Flexible"),
    ]

    nom_entreprise = models.CharField("Nom de l'entreprise", max_length=150)
    nom_contact = models.CharField("Nom du responsable", max_length=150)
    email = models.EmailField("Email")
    telephone = models.CharField("Téléphone", max_length=30)
    type_projet = models.CharField("Type de projet", max_length=25, choices=TYPE_PROJET_CHOIX)
    budget = models.CharField("Budget estimé (FCFA)", max_length=20, choices=BUDGET_CHOIX, blank=True)
    delai = models.CharField("Délai souhaité", max_length=15, choices=DELAI_CHOIX, blank=True)
    description = models.TextField("Description du projet")
    date_envoi = models.DateTimeField("Reçu le", auto_now_add=True)
    traite = models.BooleanField("Traité", default=False)
    transmis = models.BooleanField("Transmis à eSoft", default=False, editable=False)
    transmis_le = models.DateTimeField("Transmis le", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Demande de projet"
        verbose_name_plural = "Demandes de projet"
        ordering = ["-date_envoi"]

    def __str__(self):
        return f"{self.nom_entreprise} — {self.get_type_projet_display()} ({self.date_envoi:%d/%m/%Y})"


# --------------------------------------------------------------------------
# Candidatures (formulaire « Postuler ») et badges publics (vérification QR)
# --------------------------------------------------------------------------

CV_TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo
CV_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def valider_cv(fichier):
    """Vérifie l'extension, la taille et la signature réelle du fichier CV."""
    extension = os.path.splitext(fichier.name or "")[1].lower()
    if extension not in CV_SIGNATURES:
        raise ValidationError("Format non accepté : envoyez un fichier PDF, JPG ou PNG.")
    if fichier.size is not None and fichier.size > CV_TAILLE_MAX:
        raise ValidationError("Le fichier est trop volumineux (5 Mo maximum).")
    position = fichier.tell() if hasattr(fichier, "tell") else 0
    try:
        fichier.seek(0)
        debut = fichier.read(16)
    finally:
        try:
            fichier.seek(position)
        except Exception:
            pass
    if not any(debut.startswith(sig) for sig in CV_SIGNATURES[extension]):
        raise ValidationError(
            "Le contenu du fichier ne correspond pas à son extension (PDF, JPG ou PNG attendu)."
        )


class Candidature(models.Model):
    """Candidature envoyée via le bouton « Postuler » d'une offre de recrutement."""

    recrutement = models.ForeignKey(
        Recrutement, on_delete=models.PROTECT, related_name="candidatures",
        verbose_name="Offre",
    )
    nom = models.CharField("Nom", max_length=100)
    prenom = models.CharField("Prénom", max_length=100)
    email = models.EmailField("E-mail")
    telephone = models.CharField("Téléphone", max_length=30)
    diplome = models.CharField("Diplôme le plus élevé", max_length=150)
    experience_ans = models.PositiveSmallIntegerField("Années d'expérience", default=0)
    message = models.TextField("Message / motivation", blank=True)
    cv = models.FileField(
        "CV", upload_to="candidatures/", blank=True, validators=[valider_cv],
        help_text="PDF, JPG ou PNG — 5 Mo maximum.",
    )
    recu_le = models.DateTimeField("Reçue le", auto_now_add=True)
    transmis = models.BooleanField("Transmise à eSoft", default=False, editable=False)
    transmis_le = models.DateTimeField("Transmise le", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Candidature"
        verbose_name_plural = "Candidatures"
        ordering = ["-recu_le"]

    def __str__(self):
        return f"{self.prenom} {self.nom} — {self.recrutement} ({self.recu_le:%d/%m/%Y})"


class BadgePublic(models.Model):
    """Badge du personnel publié par eSoft, pour la page publique /verifier/.
    Seule l'empreinte SHA-256 du jeton du badge est stockée (jamais le jeton)."""

    STATUT_CHOIX = [
        ("valide", "Valide"),
        ("revoque", "Révoqué"),
        ("inactif", "Inactif (ancien employé)"),
    ]

    empreinte = models.CharField("Empreinte (SHA-256)", max_length=64, unique=True)
    prenom = models.CharField("Prénom", max_length=100)
    nom = models.CharField("Nom", max_length=100)
    poste = models.CharField("Poste", max_length=150, blank=True)
    division = models.CharField("Division", max_length=150, blank=True)
    matricule = models.CharField("Matricule", max_length=40, blank=True)
    statut = models.CharField("Statut", max_length=10, choices=STATUT_CHOIX, default="valide")
    recu_le = models.DateTimeField("Reçu le", auto_now_add=True)

    class Meta:
        verbose_name = "Badge public"
        verbose_name_plural = "Badges publics"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_statut_display()})"
