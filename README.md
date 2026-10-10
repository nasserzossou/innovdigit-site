# INNOV DIGIT — Site vitrine (Django)

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

## Synchronisation avec eSoft INNOV.DIGIT

La plateforme interne **eSoft INNOV.DIGIT** tourne sur le réseau local de l'entreprise : elle n'est pas joignable depuis Internet. C'est donc **toujours eSoft qui appelle le site** (toutes les 15 minutes), jamais l'inverse.

### 1. Activer l'API sur Render

1. Générer un jeton secret (au moins 32 caractères) :
   ```powershell
   python -c "import secrets;print(secrets.token_urlsafe(40))"
   ```
2. Sur Render → service du site → **Environment** → ajouter la variable `ESOFT_SYNC_TOKEN` avec ce jeton, puis redéployer.
3. Dans eSoft (page **« Site web »**, compte Administrateur), saisir l'URL du site (`https://innovdigit-site.onrender.com`) et **le même jeton**.

Sans `ESOFT_SYNC_TOKEN` (ou avec un jeton de moins de 32 caractères), l'API répond `503` : elle est désactivée. Un jeton faux reçoit `401`. Ne jamais publier ce jeton (ni dans Git, ni par message).

### 2. Adresses utilisées par eSoft

| Adresse | Rôle |
|---|---|
| `POST /api/esoft/publier/` | eSoft envoie tout ce qui doit être publié (partenaires, offres, réalisations avec leur catégorie, projets en développement, coordonnées, badges) — contrat version 2, la version 1 reste acceptée |
| `GET /api/esoft/demandes/` | eSoft récupère les messages, demandes et candidatures reçus sur le site |
| `POST /api/esoft/accuser/` | eSoft confirme la réception ; les CV transmis sont alors **supprimés du site** |
| `GET /verifier/<jeton>/` | Page publique ouverte par le QR code d'un badge du personnel (non indexée) |

### 3. Ce qui est géré depuis eSoft / ce qui reste à la main

| Rubrique du site | Géré depuis eSoft (écrasé à chaque synchronisation) |
|---|---|
| **Contactez-nous** (page Contact, pied de page, À propos, réponse « contact » de l'assistant) | **Coordonnées** : nom, slogan, adresse, ville, téléphones, e-mail, WhatsApp, horaires, Facebook, LinkedIn |
| **Annonces → Recrutement** | **Offres de recrutement** (avec date limite et bouton « Postuler ») |
| **Annonces → Projets en cours** | **Projets en développement** (projets eSoft cochés « Publier sur le site ») |
| **Ils nous font déjà confiance** (Accueil, Partenariat, À propos) | **Partenaires** (logo compris) |
| **Nos Réalisations** (Projets réalisés) | **Réalisations** avec leur **catégorie** (vitrine, e-commerce, one page, refonte, mobile, communication, autres) |
| Vérification des badges | **Badges publics** (table remplacée entièrement) |

Restent gérés à la main dans `/admin/` : les attestations, le suivi « Traité » des messages et demandes, et les éléments saisis à la main (sans « Référence eSoft ») — partenaires, offres, projets réalisés ou projets en cours.

**Coordonnées** : tant qu'eSoft n'a rien publié, le site affiche les valeurs d'origine (Niamey, Niger · innovdigitinfo@gmail.com · +227 97 42 02 07 / +227 80 36 56 50). Un champ essentiel publié vide (adresse, e-mail, téléphones) retombe aussi sur ces valeurs. Le nom est toujours affiché « INNOV DIGIT » (un « INNOV-DIGIT » ou « INNOV_DIGIT » reçu est corrigé). Les coordonnées sont visibles en lecture seule dans l'admin (« Coordonnées »).

- Un élément venant d'eSoft porte une **Référence eSoft** (colonne « Origine » dans l'admin) et affiche l'avertissement : *« Géré depuis eSoft : les modifications faites ici seront écrasées à la prochaine synchronisation »*. Modifiez-le dans eSoft, pas dans l'admin.
- Un élément retiré dans eSoft est **masqué** sur le site (« Visible sur le site » décoché), pas supprimé.
- Les éléments saisis à la main (sans référence eSoft) ne sont **jamais** modifiés par la synchronisation.
- Les **candidatures** arrivent par le bouton « Postuler » de chaque offre ouverte (page Annonces). Elles sont visibles en lecture seule dans l'admin ; les CV ne sont pas accessibles publiquement (téléchargement réservé aux comptes admin) et sont effacés du site dès qu'eSoft les a récupérés.

### 4. ⚠️ Limite importante : le disque de Render (offre gratuite) est éphémère

Sur l'offre gratuite, Render **efface la base SQLite (`db.sqlite3`) et le dossier `media/`** à chaque redéploiement ou redémarrage du service :

- le contenu publié par eSoft se **reconstruit tout seul** à la synchronisation suivante (eSoft renvoie tout à chaque fois) ;
- en revanche, **un message, une demande ou une candidature reçus sur le site et pas encore récupérés par eSoft sont perdus** si Render redémarre entre-temps. eSoft les récupère toutes les 15 minutes, ce qui réduit ce risque sans le supprimer ;
- les éléments saisis à la main dans l'admin et les images uploadées à la main sont aussi perdus à chaque redéploiement.

**Recommandé** : ajouter un disque persistant Render (monté sur le dossier `media/`) et passer à une base **PostgreSQL** (Render Postgres) pour ne plus rien perdre.
