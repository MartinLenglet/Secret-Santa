# Secret Santa

Une application locale pour organiser des échanges de cadeaux en privé : **React + TypeScript**
pour l'interface en français, **FastAPI** pour le backend Python, **SQLite** pour conserver les
événements et **Gmail SMTP** pour envoyer un mail individuel à chaque participant.

## Fonctionnalités

- Plusieurs événements : création, brouillons, duplication et suppression avec confirmation.
- De 2 à 200 participants par événement, saisis manuellement.
- Groupes d'exclusion mutuels, cumulables : couples, foyers, etc. Les membres restent participants,
  mais ne peuvent pas s'offrir de cadeaux entre eux.
- Vérification exacte de faisabilité avant tirage, y compris les impossibilités globales.
- Chaque personne donne et reçoit exactement un cadeau ; jamais à elle-même.
- Budget, devise et date du cadeau facultatifs.
- Objet et message personnalisables avec balises, aperçu fictif et mail de test.
- Tirage enregistré et verrouillé avant envoi ; progression et reprise des envois sans nouveau tirage.
- Résultats masqués par défaut, consultables seulement après avertissement et confirmation.
- Mot de passe d'application Gmail utilisé en mémoire, jamais enregistré.

## Prérequis

- [Git](https://git-scm.com/downloads) pour récupérer le dépôt (ou télécharger son archive depuis GitHub).
- [Python **3.12+**](https://www.python.org/downloads/) avec `pip` et `venv`.
  Sous Windows, activer l'ajout de Python au PATH lors de l'installation.
- [Node.js **22.18+ ou 24 LTS**](https://nodejs.org/) avec npm.
- GNU Make, facultatif, pour les commandes `make` (ou les commandes Python équivalentes ci-dessous).
- Une adresse Gmail personnelle, la validation en deux étapes et un mot de passe d'application.

Après installation de Python et Node.js, ouvrir un nouveau terminal et vérifier :

```powershell
python --version
node --version
npm.cmd --version
```

Sur macOS ou Linux, utiliser `python3` si nécessaire et `npm` à la place de `npm.cmd`.
Sur certaines distributions Linux, installer aussi le paquet `python3-venv`.

### GNU Make sous Windows

Pour installer GNU Make avec WinGet, exécuter dans PowerShell :

```powershell
winget install --id ezwinports.make --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
```

**Ouvrir ensuite un nouveau terminal** pour actualiser le PATH et vérifier :

```powershell
make --version
```

Le paquet portable provient du projet ezwinports ; WinGet vérifie l'empreinte de l'archive.
Pas besoin de Bash, WSL ou d'une modification de la politique d'exécution PowerShell.
Le lanceur utilise `npm.cmd` sous Windows pour éviter le blocage éventuel de `npm.ps1`.
Si WinGet ou Make n'est pas disponible, utiliser directement les commandes `python manage.py`
ci-dessous : elles offrent les mêmes fonctionnalités.

## Quickstart

### 1. Récupérer le projet

```powershell
git clone https://github.com/MartinLenglet/Secret-Santa.git
cd Secret-Santa
```

Il est aussi possible de télécharger et décompresser l'archive du dépôt, puis d'ouvrir un
terminal dans le dossier contenant `manage.py` et `Makefile`.
Une connexion Internet est nécessaire à la première installation pour télécharger les dépendances.

### 2. Installer les dépendances et lancer l'application

Depuis la racine du dépôt, avec GNU Make :

```powershell
make install
make dev
```

Ouvrir **http://127.0.0.1:5173**. Le frontend et le backend sont démarrés ensemble et vérifiés
par le lanceur. **Ctrl+C** arrête les deux services.

Sans GNU Make :

```powershell
python manage.py install
python manage.py dev
```

L'installation crée l'environnement Python `.venv` et installe les dépendances backend et frontend.
Il n'est pas nécessaire d'activer manuellement cet environnement ni de configurer un serveur
de base de données : SQLite est initialisé automatiquement au premier démarrage.
Pour les lancements suivants, `make dev` ou `python manage.py dev` suffit.

Le backend écoute sur `127.0.0.1:8000`, le frontend sur `127.0.0.1:5173`.
Les ports sont fixes ; s'ils sont occupés, le démarrage échoue explicitement.
Vite recharge l'interface pendant le développement. Pour appliquer un changement Python,
arrêter puis relancer : le backend n'est volontairement pas rechargé automatiquement pendant un envoi.

### Utilisation en mode construit

```powershell
make build
make start
```

Ouvrir **http://127.0.0.1:8000**. FastAPI sert alors l'interface construite et l'API :
pas de serveur Vite nécessaire à l'exécution.

### Commandes

| Make | Sans Make | Action |
|---|---|---|
| `make install` | `python manage.py install` | Créer `.venv`, installer Python et npm |
| `make dev` | `python manage.py dev` | Démarrer les deux services locaux |
| `make build` | `python manage.py build` | Vérifier TypeScript et construire le frontend |
| `make start` | `python manage.py start` | Servir l'application construite |
| `make test` | `python manage.py test` | Tests backend et frontend, sans vrai SMTP |
| `make lint` | `python manage.py lint` | Ruff et Oxlint |
| `make help` | `python manage.py help` | Aide |

Si Python porte un autre nom : `make PYTHON=python3 install`.
L'installation npm utilise le lockfile avec `npm ci` lorsqu'il existe.

## Configurer Gmail simplement

La solution retenue est **SMTP avec un mot de passe d'application**, sans projet Google Cloud
ni configuration OAuth :

1. Activer la [validation en deux étapes](https://support.google.com/accounts/answer/185839?hl=fr)
   du compte Google expéditeur.
2. Ouvrir les [mots de passe d'application](https://myaccount.google.com/apppasswords)
   et en créer un, par exemple pour « Secret Santa ».
3. Dans l'événement, renseigner l'adresse `@gmail.com` ou `@googlemail.com` de ce compte.
4. Saisir le mot de passe d'application de **16 lettres** dans le champ dédié.
   Les espaces de présentation sont acceptés. **Ne jamais saisir le mot de passe Google habituel.**
5. Cliquer sur **M'envoyer un test fictif** : le message part uniquement vers l'expéditeur,
   avec Camille et Alex comme personnages fictifs et un objet préfixé `[TEST]`.
6. Vérifier la réception, y compris les indésirables, avant l'envoi aux participants.

La connexion utilise `smtp.gmail.com:465` avec TLS et vérification du certificat.
Le mot de passe est effacé du champ à chaque opération ; il faut le saisir à nouveau pour
un autre test, un envoi ou une reprise. Ni la base, ni le stockage du navigateur, ni les journaux
applicatifs ne le conservent.

**Limites Google :** les mots de passe d'application peuvent être indisponibles pour certains
comptes d'organisation, avec Protection Avancée ou selon la méthode de validation en deux étapes.
Ils sont révoqués si le mot de passe Google change. Google recommande OAuth pour les intégrations
générales ; SMTP est choisi ici pour la simplicité d'une application locale personnelle.
Les quotas et restrictions anti-spam de Gmail s'appliquent, même sous 200 participants.

Sources : [aide Google sur les mots de passe d'application](https://support.google.com/accounts/answer/185833?hl=fr)
et [documentation Gmail SMTP](https://developers.google.com/workspace/gmail/imap/imap-smtp).

## Préparer un événement

1. Créer un événement ; renseigner son nom, l'expéditeur, et éventuellement budget et date.
2. Ajouter les participants avec des adresses uniques.
3. Ajouter les groupes d'exclusion et cocher au moins deux membres par groupe.
   Une même personne peut appartenir à plusieurs groupes.
4. Personnaliser le message, vérifier son aperçu et enregistrer le brouillon.
5. Cliquer sur **Vérifier la faisabilité**. Toute modification invalide le verdict affiché.
6. Confirmer **Effectuer le tirage** : le serveur vérifie à nouveau les règles et sauvegarde
   l'attribution de chacun. Aucun mail ne part à cette étape.
7. Saisir le mot de passe d'application et cliquer sur **Envoyer les attributions**.

Le tirage utilise un appariement biparti exact, avec un ordre de recherche aléatoire.
Il n'échoue pas simplement parce que quelques permutations essayées sont mauvaises.
Les solutions ne sont pas garanties uniformément distribuées. Les échanges réciproques
entre deux personnes restent possibles, sauf si elles partagent un groupe d'exclusion.

Après tirage, la configuration et le message sont figés, même si les mails ne sont pas encore partis.
Dupliquer l'événement pour modifier la liste ou recommencer : la copie ne contient ni attributions
ni historique d'envoi. Supprimer un événement ne rappelle pas les mails déjà envoyés.

### Balises

| Balise | Signification |
|---|---|
| `{{participant_nom}}` | Personne qui reçoit ce mail et **offre** le cadeau |
| `{{destinataire_nom}}` | Personne à qui elle doit **offrir** un cadeau |
| `{{evenement_nom}}` | Nom de l'événement |
| `{{budget}}` | Montant et devise, ou « Non précisé » |
| `{{date}}` | Date au format JJ/MM/AAAA, ou « Non précisée » |

Ces balises fonctionnent dans l'objet et dans le corps en texte simple UTF-8.
Les balises inconnues et les accolades mal formées sont refusées. Il n'y a pas de HTML,
de code exécutable ou d'évaluation de modèles. L'aperçu utilise toujours des noms fictifs.

## Envois interrompus et reprise

Le suivi distingue :

- **En attente** : pas encore tenté.
- **En cours** : tentative enregistrée avant l'appel SMTP.
- **Accepté par Gmail** : le serveur SMTP a accepté le mail, **pas une preuve de livraison**.
- **Échec** : connexion/authentification impossible ou refus SMTP explicite.
- **À vérifier dans Gmail** : coupure ou interruption après le début de la soumission.

Le lot s'arrête au premier échec ou état incertain. Une reprise conserve exactement les mêmes
attributions et ignore les mails déjà acceptés. Les états incertains nécessitent une confirmation
supplémentaire : vérifier les messages envoyés Gmail avant de réessayer.
Il est impossible de garantir un envoi « exactement une fois » après une coupure réseau :
Gmail peut avoir accepté un mail sans que l'application ait reçu sa réponse.

Garder le serveur ouvert pendant l'envoi. Après un redémarrage, les tentatives restées en cours
deviennent incertaines. Un verrou système interdit à deux serveurs d'utiliser simultanément la même
base ; lancer un seul processus backend, sans plusieurs workers.

## Données et confidentialité

Par défaut, la base est placée **hors du dépôt**, pour éviter notamment sa synchronisation OneDrive :

- Windows : `%LOCALAPPDATA%\SecretSanta\santa.sqlite3`.
- Autres systèmes : `~/.local/share/SecretSanta/santa.sqlite3` (sauf `LOCALAPPDATA` défini).

Pour choisir un autre emplacement, dans le terminal qui lancera l'application :

```powershell
$env:SANTA_DATABASE = Join-Path $env:LOCALAPPDATA 'SecretSantaData\santa.sqlite3'
make dev
```

Ne pas placer la base dans un dossier partagé ou synchronisé si vous souhaitez la garder sur
la machine. Pour une sauvegarde cohérente, arrêter le serveur avant de copier la base.
SQLite, ses éventuels fichiers WAL/SHM et le fichier de verrou ne doivent pas être versionnés.

Cette application n'a **pas de comptes ni d'authentification** : elle est conçue pour la machine
de l'organisateur, sur `127.0.0.1`. Les origines web autorisées sont limitées aux ports locaux prévus,
les mutations utilisent JSON et l'API ne fournit pas de CORS permissif.
**Ne pas exposer les ports sur Internet ou le réseau local.** Un hébergement nécessiterait une
authentification, HTTPS et une stratégie de protection des données supplémentaire.

Les attributions ne sont jamais incluses dans les réponses courantes de l'API ni préchargées
par l'interface. Leur consultation nécessite une action distincte puis une confirmation explicite.
Elles restent cependant **en clair dans SQLite**, tout comme les noms et adresses mail.
Un utilisateur ayant accès à la machine peut donc les lire. Les mails peuvent aussi apparaître
dans les messages envoyés Gmail. Le bouton de révélation prévient les consultations accidentelles,
ce n'est pas une barrière d'autorisation.

## Structure et développement

Les consignes destinées aux agents sont réparties dans [AGENTS.md](./AGENTS.md),
[frontend/AGENTS.md](./frontend/AGENTS.md) et [backend/AGENTS.md](./backend/AGENTS.md).

```text
backend/
  santa/
    app.py        API, transitions et orchestration
    schemas.py    Validation et contrat des événements
    database.py   SQLite et récupération des envois interrompus
    matching.py   Faisabilité et tirage exacts
    mail.py       Rendu des balises et SMTP Gmail
  tests/          Tests API, tirage et transport simulé
frontend/
  src/            Interface React, styles et tests
Makefile          Commandes communes
manage.py         Installation et lancement multiplateformes
```

La documentation interactive de l'API est disponible sur **http://127.0.0.1:8000/docs**.
Les brouillons portent une révision : une sauvegarde concurrente ou un tirage sur une version
périmée renvoie une erreur au lieu d'écraser des données.

Les tests comparent notamment le verdict du moteur à une recherche exhaustive sur de petits
cas, couvrent les groupes imbriqués, 200 participants, les échecs SMTP, la reprise, les verrous,
la persistance et la confirmation de révélation. Aucun test automatisé n'envoie de mail réel.
L'envoi réel est à valider avec le bouton de test et votre propre compte Gmail.