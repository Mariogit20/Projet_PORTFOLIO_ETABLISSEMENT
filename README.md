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