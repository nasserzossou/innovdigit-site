/* ==========================================================================
   INNOV-DIGIT - Script JavaScript principal
   Gère : menu mobile, animation au scroll, formulaires (projet, contact,
          partenariat), chatbot FAQ, filtres projets, images manquantes,
          slider partenaires, onglets annonces
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    // --- Menu mobile (hamburger) ---
    const boutonHamburger = document.querySelector('.hamburger');
    const menuLiens = document.querySelector('.menu-liens');

    if (boutonHamburger && menuLiens) {
        boutonHamburger.addEventListener('click', function () {
            boutonHamburger.classList.toggle('actif');
            menuLiens.classList.toggle('ouvert');
        });

        const liens = document.querySelectorAll('.menu-liens a');
        liens.forEach(function (lien) {
            lien.addEventListener('click', function () {
                boutonHamburger.classList.remove('actif');
                menuLiens.classList.remove('ouvert');
            });
        });
    }

    // --- Animation "fade-in" au scroll ---
    const elementsAnimes = document.querySelectorAll('.au-scroll');

    if (elementsAnimes.length > 0) {
        const observateur = new IntersectionObserver(function (entrees) {
            entrees.forEach(function (entree) {
                if (entree.isIntersecting) {
                    entree.target.classList.add('visible');
                    observateur.unobserve(entree.target);
                }
            });
        }, {
            threshold: 0.15
        });

        elementsAnimes.forEach(function (element) {
            observateur.observe(element);
        });
    }

    // --- Formulaires (Projet, Contact, Partenariat) ---
    // Ils sont envoyés normalement au serveur Django, qui enregistre la demande puis affiche la confirmation
    // (?envoye=1). L'ancien code bloquait l'envoi et affichait une fausse confirmation : rien n'était enregistré.

    // --- Formulaire de partenariat (avec réservation de rendez-vous) ---
    const champDateRdv = document.querySelector('#date-rdv');

    // Empêche de choisir une date de rendez-vous dans le passé
    if (champDateRdv) {
        const aujourdHui = new Date().toISOString().split('T')[0];
        champDateRdv.setAttribute('min', aujourdHui);
    }

    // --- Chatbot FAQ (statique, sans IA) ---
    const bulleChatbot = document.querySelector('#chatbot-bulle');
    const fenetreChatbot = document.querySelector('#chatbot-fenetre');
    const boutonFermerChatbot = document.querySelector('#chatbot-fermer');
    const corpsChatbot = document.querySelector('#chatbot-corps');
    const optionsChatbot = document.querySelector('#chatbot-options');

    const questionsReponses = {
        "services": {
            question: "Quels services proposez-vous ?",
            reponse: "Développement logiciel, services IT, cybersécurité, formations & conseil, IA, big data, hébergement, conception, communication et vente de matériel informatique."
        },
        "devis": {
            question: "Comment obtenir un devis ?",
            reponse: "Rendez-vous sur la page \"Confiez-nous votre projet\" et remplissez le formulaire. Nous vous recontacterons rapidement avec une proposition adaptée."
        },
        "delai": {
            question: "Quels sont vos délais habituels ?",
            reponse: "Cela dépend du projet : entre 1 et 3 mois pour un site web ou une petite application, et jusqu'à 6 mois pour des projets plus complexes."
        },
        "contact": {
            question: "Comment vous contacter directement ?",
            reponse: "Écrivez-nous à innovdigitinfo@gmail.com ou appelez le +227 97 42 02 07 / +227 80 36 56 50. Nous sommes basés à Niamey, Niger."
        }
    };

    if (bulleChatbot && fenetreChatbot) {

        bulleChatbot.addEventListener('click', function () {
            fenetreChatbot.classList.toggle('ouverte');
        });

        if (boutonFermerChatbot) {
            boutonFermerChatbot.addEventListener('click', function () {
                fenetreChatbot.classList.remove('ouverte');
            });
        }

        if (optionsChatbot) {
            optionsChatbot.addEventListener('click', function (evenement) {
                const boutonClique = evenement.target.closest('.option-chatbot');
                if (!boutonClique) return;

                const cle = boutonClique.dataset.cle;
                const item = questionsReponses[cle];
                if (!item) return;

                const messageUtilisateur = document.createElement('div');
                messageUtilisateur.className = 'message-utilisateur';
                messageUtilisateur.textContent = item.question;
                corpsChatbot.appendChild(messageUtilisateur);

                setTimeout(function () {
                    const messageBot = document.createElement('div');
                    messageBot.className = 'message-bot';
                    messageBot.textContent = item.reponse;
                    corpsChatbot.appendChild(messageBot);
                    corpsChatbot.scrollTop = corpsChatbot.scrollHeight;
                }, 500);

                corpsChatbot.scrollTop = corpsChatbot.scrollHeight;
            });
        }
    }

    // --- Filtres de la page "Projets Réalisés" ---
    const boutonsFiltres = document.querySelectorAll('.filtre-btn');
    const cartesProjets = document.querySelectorAll('.carte-projet');

    if (boutonsFiltres.length > 0) {
        boutonsFiltres.forEach(function (bouton) {
            bouton.addEventListener('click', function () {
                const categorie = bouton.dataset.categorie;

                boutonsFiltres.forEach(function (b) {
                    b.classList.remove('actif');
                });
                bouton.classList.add('actif');

                cartesProjets.forEach(function (carte) {
                    if (categorie === 'tous' || carte.dataset.categorie === categorie) {
                        carte.classList.remove('cachee');
                    } else {
                        carte.classList.add('cachee');
                    }
                });
            });
        });
    }

    // --- Gestion des images manquantes (affiche un espace réservé) ---
    document.querySelectorAll('.image-projet img').forEach(function (image) {
        image.addEventListener('error', function () {
            image.style.display = 'none';
            image.parentElement.classList.add('image-manquante');
            image.parentElement.innerHTML += '<i class="bi bi-image"></i><span>Image à ajouter</span>';
        });
    });

    // --- Slider des logos partenaires (défilement en boucle infinie) ---
    const pisteLogos = document.querySelector('.slider-partenaires-piste');

    if (pisteLogos) {
        const logosOriginaux = Array.from(pisteLogos.children);
        logosOriginaux.forEach(function (logo) {
            const clone = logo.cloneNode(true);
            clone.setAttribute('aria-hidden', 'true');
            pisteLogos.appendChild(clone);
        });
    }

    // --- Onglets de la page Annonces ---
    const onglets = document.querySelectorAll('.onglet-annonce');
    const contenusOnglets = document.querySelectorAll('.contenu-onglet-annonce');

    if (onglets.length > 0) {
        onglets.forEach(function (onglet) {
            onglet.addEventListener('click', function () {
                const cible = onglet.dataset.cible;

                onglets.forEach(function (o) { o.classList.remove('actif'); });
                onglet.classList.add('actif');

                contenusOnglets.forEach(function (contenu) {
                    contenu.classList.toggle('actif', contenu.id === cible);
                });
            });
        });
    }

});