# 🎓 Système de Gestion Scolaire (GestScolaire)

**GestScolaire** est une application web métier développée avec **Django**. Conçue spécifiquement pour s'adapter au découpage administratif et éducatif de Madagascar, elle permet la gestion centralisée de l'infrastructure scolaire et des ressources humaines, tout en appliquant des règles strictes de sécurité et de cloisonnement des données.

---

## 🌟 Fonctionnalités Principales

### 1. 📍 Modélisation de la Hiérarchie Géographique
Le système respecte strictement l'arborescence administrative de l'Éducation Nationale :
* **DREN** (Direction Régionale de l'Éducation Nationale)
* **CISCO** (Circonscription Scolaire)
* **ZAP** (Zone d'Animation Pédagogique)
* **Fokontany** (Quartier/Village)
* **Établissements** (Lycées, CEG, EPP...)

L'ajout d'entités bénéficie de formulaires intelligents avec **autocomplétion en cascade**, garantissant l'intégrité de la base de données.

### 2. 🔐 Sécurité et Cloisonnement des Données (Row-Level Security)
C'est le cœur sécuritaire de l'application. Le système intègre un accès basé sur les rôles (RBAC) couplé à une restriction géographique multiniveaux :
* Un administrateur national a une vue globale.
* Un utilisateur restreint à une zone spécifique (ex: CISCO d'Antsirabe I) **ne verra, ne modifiera et ne pourra ajouter que les données appartenant strictement à sa juridiction**.
* Les vues, formulaires et barres de recherche s'adaptent dynamiquement au profil de l'utilisateur connecté.

### 3. 👥 Gestion des Ressources Humaines
* **Portfolios :** Enregistrement du personnel éducatif avec numéro de CIN et lien vers leurs portefeuilles numériques/CV.
* **Affectations (Présences) :** Suivi chronologique des assignations des professeurs/agents dans les différents établissements.

### 4. 📊 Tableau de Bord et Interface Moderne
* Design entièrement responsive basé sur **Bootstrap 5**.
* Tableaux de données interactifs propulsés par **DataTables** (recherche, pagination, tri).
* Exportation instantanée des tableaux affichés au format **PDF, Excel, CSV**, ou impression directe.

### 5. 💾 Sauvegarde et Restauration (JSON)
* **Exportation** de l'intégralité de la base de données SQLite en un clic (fichier d'archive JSON daté).
* **Importation** pour mettre à jour ou compléter la base.
* Option **"Hard Reset"** sécurisée : permet de purger entièrement l'historique et de recréer l'arborescence pure à partir d'un fichier de sauvegarde.

---

## 🛠️ Technologies Utilisées

* **Backend :** Python 3.10+, Framework Django 5.x
* **Base de données :** SQLite (par défaut)
* **Frontend :** HTML5, CSS3, JavaScript, jQuery
* **Framework UI :** Bootstrap 5.3
* **Librairies tierces :** * `python-Levenshtein` (algorithme de recherche approximative/autocomplétion)
  * `DataTables` (grilles de données interactives)

---

## 🚀 Installation et Déploiement Local

Suivez ces étapes pour faire tourner le projet sur votre propre machine.

### 1. Récupération du projet
Ouvrez votre terminal et clonez le dépôt :
```bash
git clone [https://github.com/Mariogit20/logiciel-scolaire.git](https://github.com/Mariogit20/logiciel-scolaire.git)
cd logiciel-scolaire


-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

C'est VRAIMENT TRES TRES TRES TRES IMPORTANT :

Conseil d'utiliser la BASE DE DONNEES Postgres QUE d'utiliser la BASE DE DONNEES SQLite :

Vous :       Une question : La basse de données Postgres est t elle préférable pour ce projet par rapport à Sqlite ?
Gemini 3.1 Pro :        La réponse courte : Oui, absolument. Pour la mise en production de ce projet, un moteur de base de données comme PostgreSQL est très fortement recommandé par rapport à SQLite.
Voici pourquoi, en prenant en compte l'architecture de votre système :
1. La gestion des accès simultanés (Le point faible de SQLite)
SQLite est fantastique pour le développement sur votre ordinateur car tout est stocké dans un simple fichier (db.sqlite3). Cependant, lors d'une opération d'écriture (un ajout ou une modification), SQLite verrouille la base de données entière.
Dans un système hiérarchisé impliquant potentiellement de multiples utilisateurs (comme des responsables de différentes DREN, CISCO ou directeurs d'établissements) qui se connectent pour modifier des données de présence ou des portfolios en même temps, SQLite va créer des bouchons et générer des erreurs de type « database is locked ».
2. La robustesse de PostgreSQL
PostgreSQL est un véritable serveur de base de données conçu pour la production. Il gère parfaitement la concurrence : plusieurs utilisateurs de différentes régions de Madagascar peuvent écrire et lire des données simultanément sans aucune perte de performance ni conflit. Il est également beaucoup plus strict et sécurisé concernant l'intégrité de vos données complexes (comme vos modèles conceptuels).
________________________________________
⚠️ Le facteur "PythonAnywhere"
Il y a un détail logistique très important à prendre en compte pour votre hébergement :
•	Comptes gratuits : PythonAnywhere ne propose pas PostgreSQL sur son offre gratuite. Ils proposent MySQL (qui est également un excellent choix pour la production, gère très bien la concurrence, et remplacera parfaitement SQLite).
•	Comptes payants (Hacker et plus) : Vous avez accès à PostgreSQL.
Ma recommandation pour la suite
Ne bloquez pas votre déploiement pour changer de base de données tout de suite !
L'approche la plus prudente est de faire d'abord un premier déploiement avec votre SQLite actuel (le fichier db.sqlite3 a d'ailleurs été envoyé sur GitHub lors de votre push). Cela nous permettra de vérifier que l'application web s'affiche correctement, que le code s'exécute, et que l'interface de connexion fonctionne.
Une fois que votre application sera en ligne et stable, nous pourrons changer quelques lignes dans votre fichier settings.py pour la connecter à MySQL ou PostgreSQL de manière définitive.

