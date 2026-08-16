# INNOV-DIGIT — Site vitrine (Django)

## Lancer le site en local (Windows PowerShell)

```powershell
# 1. Créer et activer un environnement virtuel
python -m venv venv
venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Appliquer les migrations (la base de données est vide dans ce zip)
python manage.py migrate

# 4. Importer les données de démarrage (projets, attestations, partenaires, annonces)
python manage.py seed_projets

# 5. Créer ton propre compte admin
python manage.py createsuperuser

# 6. Lancer le serveur
python manage.py runserver
```

Le site est accessible sur http://127.0.0.1:8000/

## Compte admin

Créé à l'étape 5 ci-dessus avec `createsuperuser` (choisis ton propre nom d'utilisateur et mot de passe).

## Ce qui est géré depuis l'admin (`/admin/`)

| Section admin | Où c'est affiché sur le site |
|---|---|
| **Projets réalisés** | Page "Projets Réalisés" (avec filtre par catégorie, dont "Travaux de Communication") |
| **Attestations** | Page "Témoignages", section "Attestations de travail" |
| **Partenaires** | Page "Accueil" et page "Partenariat", section "Ils nous font déjà confiance" |
| **Offres de recrutement** | Page "Annonces", onglet "Recrutement" |
| **Projets en cours** | Page "Annonces", onglet "Projets en cours" |
| **Messages de contact** | Lecture seule — messages reçus via le formulaire de la page "Contact" |
| **Demandes de partenariat** | Lecture seule — demandes reçues via le formulaire de la page "Partenariat" |
| **Demandes de projet** | Lecture seule — demandes reçues via le formulaire "Confiez-nous votre projet" |

Pour chaque section (sauf Messages de contact) : décoche "Visible sur le site" pour masquer un élément sans le supprimer, et utilise "Ordre d'affichage" pour réordonner.

Les images (projets, attestations, partenaires) sont pour l'instant des **placeholders provisoires** (fond bleu/gris + nom). Remplace-les en éditant chaque élément dans l'admin et en uploadant la vraie image.

## Formulaires — tous fonctionnels maintenant

⚠️ **Point important** : sur ton site HTML d'origine, les 3 formulaires (Contact, Partenariat, Confiez-nous votre projet) ne faisaient qu'afficher un faux message de confirmation en JavaScript — **rien n'était réellement envoyé ou enregistré**. Personne ne recevait les messages.

Les 3 formulaires sont maintenant réellement branchés à la base de données, chacun visible et gérable dans `/admin/` (avec case à cocher "Traité" pour ton suivi) :

| Formulaire | Page | Section admin |
|---|---|---|
| Contact | `/contact/` | Messages de contact |
| Partenariat | `/partenariat/` | Demandes de partenariat |
| Confiez-nous votre projet | `/confiez-nous-projet/` | Demandes de projet |

Tous testés de bout en bout (soumission réelle → enregistrement en base vérifié).

## Structure du projet

```
innovdigit/
├── config/          # Réglages Django (settings, urls principales)
├── vitrine/         # App principale (modèle Projet, vues, admin)
│   ├── static/      # CSS, JS, images fixes du site
│   └── templates/vitrine/
├── templates/        # Tous les templates (base.html + pages)
├── media/projets/    # Images de projets uploadées via l'admin
├── db.sqlite3        # Base de données
└── manage.py
```

## Prochaine étape : hébergement gratuit sur Render.com

À faire dans un prochain échange une fois que tu as vérifié que tout marche bien en local.
