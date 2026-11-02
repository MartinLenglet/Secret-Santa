# Guide du dépôt

## Portée et repères

Ces consignes s'appliquent à tout le dépôt. Les guides [frontend](./frontend/AGENTS.md) et
[backend](./backend/AGENTS.md) les complètent dans leurs répertoires respectifs.
Le [README](./README.md) décrit l'installation sur un nouveau poste, Gmail et les parcours utilisateur :
le maintenir comme guide reproductible, pas comme compte rendu d'une machine particulière.

- [frontend/](./frontend/) : interface React et TypeScript, construite avec Vite.
- [backend/santa/](./backend/santa/) : API FastAPI, SQLite, tirage et transport Gmail.
- [manage.py](./manage.py) : installation et orchestration multiplateformes.
- [Makefile](./Makefile) : délègue au lanceur Python, sans dépendance à Bash.

## Installation et validation

Depuis la racine, avec Python 3.12+ et Node.js 22.18+ ou 24 LTS :

```text
python manage.py install
python manage.py dev
python manage.py test
python manage.py lint
python manage.py build
```

Chaque commande est aussi disponible via `make <commande>`. Sous Windows, utiliser `npm.cmd`
pour les commandes npm directes ; ne pas modifier la politique PowerShell.
Le lanceur utilise `.venv` sans activation et `npm ci` si le lockfile existe.

Le développement utilise les ports 5173 (Vite) et 8000 (API), sur `127.0.0.1`.
Après un build, `python manage.py start` sert l'ensemble sur le port 8000.
Le backend ne se recharge pas automatiquement : le redémarrer après une modification Python.
Ne pas interrompre un envoi réel pour appliquer un changement.

Pour du code, exécuter les tests ciblés de la partie modifiée, puis les contrôles pertinents ;
vérifier les deux côtés si le contrat API change. Une modification documentaire seule ne nécessite
pas de relancer les suites. Garder les dépendances frontend et leur lockfile cohérents.

## Invariants communs

- Application locale sans authentification : ne pas exposer les services sur le réseau ni élargir
  les origines/hôtes autorisés sans revoir explicitement ce modèle.
- Chaque participant donne et reçoit exactement un cadeau, jamais à lui-même.
  Les exclusions d'un groupe sont mutuelles et celles des groupes se cumulent.
- Après tirage, l'événement est figé. Une duplication repart sans résultats ni historique d'envoi.
- Préserver les confirmations de révélation, suppression et reprise incertaine.
  Ne jamais précharger les attributions dans les réponses courantes ou l'interface.
- Ne jamais sauvegarder ni journaliser le secret Gmail. Ne pas utiliser de vrais identifiants
  ou envoyer de vrais mails dans les tests et exemples.
- Les données SQLite sont en clair : ne pas versionner bases, fichiers annexes, secrets,
  environnements virtuels, dépendances installées ou builds.
- Conserver l'interface et les messages utilisateur en français, avec des erreurs explicites.
  Mettre à jour la documentation directement concernée lors d'un changement de comportement.
