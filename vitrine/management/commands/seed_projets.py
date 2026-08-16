"""
Commande pour importer les projets existants (venant de l'ancien projets-realises.html)
dans la base de données Django.

Usage : python manage.py seed_projets
"""
import os
from django.core.files import File
from django.core.management.base import BaseCommand
from vitrine.models import Projet, Attestation, Partenaire, Recrutement, ProjetEnCours

MEDIA_PROJETS = os.path.join("media", "projets")
MEDIA_ATTESTATIONS = os.path.join("media", "attestations")
MEDIA_PARTENAIRES = os.path.join("media", "partenaires")

DONNEES_ATTESTATIONS = [
    dict(client_nom="ONG KDR", description="Attestation de prestation - Site web",
         image_fichier="attestation-kdr.jpg", ordre=10),
    dict(client_nom="ABSANA Express", description="Attestation de prestation - Site web",
         image_fichier="attestation-absana.jpg", ordre=20),
    dict(client_nom="TEDx - ADU", description="Attestation de participation - Communication",
         image_fichier="attestation-tedx.jpg", ordre=30),
]

DONNEES_PARTENAIRES = [
    dict(nom=f"Partenaire {i}", image_fichier=f"partenaire-{i}.png", ordre=i * 10)
    for i in range(1, 7)
]

DONNEES_RECRUTEMENTS = [
    dict(titre="Développeur(se) Web / Mobile", lieu="Niamey, Niger",
         type_contrat="temps_plein", statut="ouvert",
         description="INNOV-DIGIT recherche un(e) développeur(se) motivé(e), à l'aise avec "
                      "Django, React Native ou les technologies web modernes, pour rejoindre "
                      "l'équipe sur des projets clients variés.",
         ordre=10),
    dict(titre="Chargé(e) de Communication", lieu="Niamey, Niger",
         type_contrat="temps_partiel", statut="ouvert",
         description="Gestion des réseaux sociaux, création de contenu et accompagnement des "
                      "clients dans leur stratégie de communication digitale.",
         ordre=20),
]

DONNEES_PROJETS_EN_COURS = [
    dict(titre="Refonte plateforme e-commerce locale", domaine="Développement web",
         livraison_estimee="à confirmer", statut="en_cours",
         description="Modernisation complète d'une boutique en ligne locale, incluant "
                      "catalogue produits, paiement et tableau de bord de gestion.",
         ordre=10),
    dict(titre="Module Big Data - Suivi statistique", domaine="Analyse de données",
         livraison_estimee="à confirmer", statut="en_cours",
         description="Développement d'un module d'analyse de données pour un client, afin de "
                      "visualiser et exploiter ses statistiques internes.",
         ordre=20),
    dict(titre="Application Dépannage Express - v2", domaine="Application mobile",
         livraison_estimee="à confirmer", statut="en_cours",
         description="Nouvelle version de l'application mettant en relation clients et "
                      "artisans, avec ajout de fonctionnalités de paiement et de notation.",
         ordre=30),
]

DONNEES_PROJETS = [
    dict(titre="ONG OEDAS", categorie="vitrine", etiquette="Site Vitrine",
         contexte="L'ONG OEDAS souhaitait une présence en ligne pour présenter ses missions à des partenaires et bailleurs potentiels.",
         objectif_atteint="Un site vitrine clair, présentant les actions de terrain et facilitant la prise de contact.",
         image_fichier="ong-oedas.jpg", ordre=10),

    dict(titre="ONG KDR", categorie="vitrine", etiquette="Site Vitrine",
         contexte="Besoin d'un site simple pour présenter les activités de l'ONG et centraliser les moyens de contact.",
         objectif_atteint="Une vitrine professionnelle, facilement mise à jour, valorisant les actions menées sur le terrain.",
         image_fichier="ong-kdr.jpg", ordre=20),

    dict(titre="ABSANA Express", categorie="vitrine", etiquette="Site Vitrine",
         contexte="L'entreprise de transport et livraison avait besoin d'une image professionnelle en ligne.",
         objectif_atteint="Un site présentant clairement les services de transport et facilitant la prise de contact client.",
         image_fichier="absana-express.jpg", ordre=30),

    dict(titre="TEDx - ADU", categorie="onepage", etiquette="One Page",
         contexte="L'événement TEDx ADU nécessitait une page dédiée pour informer et inscrire les participants.",
         objectif_atteint="Une page événementielle claire, avec présentation des intervenants et du programme.",
         image_fichier="tedx-adu.jpg", ordre=40),

    dict(titre="Boutique Sahel Style", categorie="ecommerce", etiquette="E-Commerce",
         contexte="Exemple de projet démontrant nos capacités en boutique en ligne pour un commerçant local.",
         objectif_atteint="Une maquette fonctionnelle avec catalogue produits, panier et simulation de paiement.",
         image_fichier="boutique-sahel.jpg", ordre=50, est_concept=True),

    dict(titre="Refonte IBRA Service", categorie="refonte", etiquette="Refonte",
         contexte="Le site existant d'IBRA Service nécessitait une modernisation de son image en ligne.",
         objectif_atteint="Une refonte complète avec un design moderne et une navigation simplifiée.",
         image_fichier="refonte-ibra-service.jpg", ordre=60, est_concept=True),

    dict(titre="SONILOGA - Zéro Impression", categorie="autres", etiquette="Dématérialisation",
         contexte="L'entreprise cherchait à réduire ses coûts et son impact environnemental liés à l'impression papier.",
         objectif_atteint="Une solution de dématérialisation des processus internes, réduisant significativement les impressions.",
         image_fichier="soniloga-zero-impression.jpg", ordre=70),

    dict(titre="Lafia Jiki Séro - Sahel", categorie="autres", etiquette="Projet Social",
         contexte="Des communautés du Sahel avaient un accès limité à certains services essentiels.",
         objectif_atteint="Un accompagnement numérique visant à faciliter l'accès des populations à ces services.",
         image_fichier="lafia-jiki-sero.jpg", ordre=80),

    dict(titre="IBRA Service", categorie="autres", etiquette="Services IT",
         contexte="L'entreprise avait besoin d'un suivi régulier de son parc informatique et de dépannages rapides.",
         objectif_atteint="Installation, maintenance préventive et dépannage réactif du matériel informatique.",
         image_fichier="ibra-service-maintenance.jpg", ordre=90),

    dict(titre="1 Jour Un Miracle", categorie="autres", etiquette="Accompagnement",
         contexte="L'initiative avait besoin d'un accompagnement numérique et technique pour ses actions.",
         objectif_atteint="Un support technique fiable, facilitant la réalisation de l'initiative \"1 Jour Un Miracle\".",
         image_fichier="1-jour-un-miracle.jpg", ordre=100),
]


class Command(BaseCommand):
    help = "Importe les projets existants (avec images placeholder) dans la base de données."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Supprime tous les projets existants avant l'import."
        )

    def _importer(self, modele, donnees, dossier_media, champ_image, champ_unique):
        nb_crees = 0
        for data in donnees:
            data = dict(data)
            valeur_unique = data[champ_unique]
            if modele.objects.filter(**{champ_unique: valeur_unique}).exists():
                self.stdout.write(f"— déjà présent, ignoré : {valeur_unique}")
                continue

            image_fichier = data.pop("image_fichier", None)
            instance = modele(**data)

            if image_fichier:
                chemin_image = os.path.join(dossier_media, image_fichier)
                if os.path.exists(chemin_image):
                    with open(chemin_image, "rb") as f:
                        getattr(instance, champ_image).save(image_fichier, File(f), save=False)

            instance.save()
            nb_crees += 1
            self.stdout.write(self.style.SUCCESS(f"+ créé : {valeur_unique}"))
        return nb_crees

    def handle(self, *args, **options):
        if options["reset"]:
            for modele in [Projet, Attestation, Partenaire, Recrutement, ProjetEnCours]:
                nb_supprimes, _ = modele.objects.all().delete()
                self.stdout.write(self.style.WARNING(f"{nb_supprimes} {modele._meta.verbose_name_plural} supprimé(s)."))

        total = 0
        self.stdout.write("\n--- Projets réalisés ---")
        total += self._importer(Projet, DONNEES_PROJETS, MEDIA_PROJETS, "image", "titre")

        self.stdout.write("\n--- Attestations ---")
        total += self._importer(Attestation, DONNEES_ATTESTATIONS, MEDIA_ATTESTATIONS, "image", "client_nom")

        self.stdout.write("\n--- Partenaires ---")
        total += self._importer(Partenaire, DONNEES_PARTENAIRES, MEDIA_PARTENAIRES, "logo", "nom")

        self.stdout.write("\n--- Recrutements ---")
        total += self._importer(Recrutement, DONNEES_RECRUTEMENTS, "", "", "titre")

        self.stdout.write("\n--- Projets en cours ---")
        total += self._importer(ProjetEnCours, DONNEES_PROJETS_EN_COURS, "", "", "titre")

        self.stdout.write(self.style.SUCCESS(f"\nTerminé : {total} élément(s) créé(s) au total."))
