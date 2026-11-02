# Guide backend

Complète le [guide global](../AGENTS.md) pour ce répertoire.

## Architecture

- [santa/app.py](./santa/app.py) : factory `create_app`, routes `/api`, transactions et orchestration.
- [santa/schemas.py](./santa/schemas.py) : validation Pydantic, contrats, balises et secret Gmail.
- [santa/database.py](./santa/database.py) : modèles SQLAlchemy, SQLite et reprise après interruption.
- [santa/matching.py](./santa/matching.py) : graphe d'exclusions et appariement parfait.
- [santa/mail.py](./santa/mail.py) : rendu texte et Gmail SMTP.
- [tests/](./tests/) : API, moteur de tirage et transport simulé.

## Commandes

Installer depuis la racine avec `python manage.py install`. Depuis la racine, sous Windows :

```text
.\.venv\Scripts\python.exe -m pytest backend/tests/test_api.py
.\.venv\Scripts\python.exe -m pytest backend/tests/test_matching.py backend/tests/test_mail.py
.\.venv\Scripts\python.exe -m ruff check backend manage.py
.\.venv\Scripts\python.exe -m ruff format backend manage.py
```

Sur macOS/Linux, remplacer l'exécutable par `.venv/bin/python`.
Configuration et dépendances dans [pyproject.toml](./pyproject.toml), Python 3.12+.
Ruff contrôle le format des imports et les règles configurées ; suivre les services existants.

## Contrats et invariants

- Valider via Pydantic : champs inconnus refusés, adresses et identifiants uniques,
  groupes avec au moins deux membres existants, maximum 200 participants.
  Les objets de mails et les noms ne doivent pas permettre d'injection d'en-têtes.
- Conserver un moteur exact commun à la faisabilité et au tirage, sans abandon après un nombre
  arbitraire de permutations. Ne pas annoncer une distribution uniforme des solutions.
- Sauvegardes et tirages utilisent une révision et une transition transactionnelle depuis
  `draft`. Empêcher les doubles tirages, les lots concurrents et la suppression pendant l'envoi.
- Ne pas inclure les attributions dans les vues courantes ou le suivi d'envoi.
  La route dédiée de révélation exige une confirmation explicite.
- Les balises sont une substitution contrôlée, pas un moteur de templates exécutable.
  Le mail de test part uniquement vers l'expéditeur, avec des données fictives.
- Le compte Gmail authentifié est l'expéditeur. Préserver TLS, vérification du certificat et délais.
  Ne pas persister le mot de passe ni le reprendre dans les erreurs de validation ou les journaux.
- Enregistrer l'intention avant SMTP et son résultat après. « Accepté » ne signifie pas « livré ».
  Reprendre les mêmes attributions, ignorer les succès et confirmer les états incertains.
  Ne pas masquer les erreurs par des résultats de succès.

## Stockage et tests

`SANTA_DATABASE` permet de choisir le fichier SQLite ; par défaut il est hors du dépôt
(voir [README](../README.md#données-et-confidentialité)).
Un verrou interprocessus protège la base pendant la vie du serveur : un seul worker,
pas de second serveur sur la même base. Au démarrage, les tentatives interrompues deviennent incertaines.
Préserver les hôtes/origines locaux et les mutations JSON sans CORS permissif.

Utiliser une base temporaire et un transport injecté via `create_app` dans les tests ;
ne jamais utiliser la base réelle de l'organisateur ni envoyer de mails réels.
Étendre les tests d'invariants du tirage, de conflits, de persistance et de reprise si ces
comportements changent. Pour le moteur, conserver la comparaison exhaustive sur de petits cas.
