# Guide frontend

Complète le [guide global](../AGENTS.md) pour ce répertoire.

## Architecture

- [src/App.tsx](./src/App.tsx) : liste des événements, sélection, création et navigation.
- [src/Editor.tsx](./src/Editor.tsx) : brouillon, participants, groupes, message, tirage et envois.
- [src/Confirm.tsx](./src/Confirm.tsx) : dialogue de confirmation.
- [src/api.ts](./src/api.ts) : types partagés côté client, requêtes JSON et erreurs API.
- [src/index.css](./src/index.css) et [src/App.css](./src/App.css) : styles globaux et composants.
- [vite.config.ts](./vite.config.ts) : proxy `/api`, serveur local et configuration Vitest.

## Commandes

Installer depuis la racine avec `python manage.py install`. Depuis `frontend/` :

```text
npm run dev
npm run build
npm run lint
npm test
npm test -- src/Editor.test.tsx
npm test -- src/App.test.tsx
```

Sous Windows, remplacer `npm` par `npm.cmd`.
Le serveur Vite seul nécessite une API déjà démarrée ; préférer le lanceur global pour les deux.
Le build vérifie TypeScript avant de produire `dist/`. Le typage est strict ;
conserver les types du client alignés avec les schémas backend, sans contournement par `any`.

## Comportements à préserver

- Utiliser le client `api` et des chemins relatifs `/api`, sans adresse backend codée en dur.
  Les données sensibles ne doivent pas être mises en cache.
- Toute modification du brouillon invalide la faisabilité et l'aperçu. Le serveur reste
  l'autorité finale pour la validation et le verrouillage.
- Sauvegarder avec la révision courante et afficher les conflits plutôt qu'écraser les données.
  Préserver l'avertissement de navigation pour un brouillon non enregistré.
- L'aperçu et le mail de test utilisent des personnages fictifs. Lancer le tirage n'envoie pas de mail.
- Ne charger les attributions qu'après confirmation explicite, puis permettre de les masquer.
  Purger les résultats révélés lors de la sortie de l'éditeur.
- Garder le secret Gmail uniquement en mémoire, l'effacer du champ après utilisation ;
  jamais de stockage navigateur, URL ou journal pour ce secret.
- Pendant un envoi, désactiver les actions incompatibles et actualiser la progression sans
  révéler le destinataire du cadeau. Une reprise incertaine exige une confirmation de doublon.
- Utiliser des libellés français, des champs étiquetés, des états d'erreur/statut accessibles
  et des dialogues utilisables au clavier. Garder la mise en page responsive.

## Tests

Vitest avec jsdom et Testing Library ; initialisation dans [src/test-setup.ts](./src/test-setup.ts).
Les tests existants simulent `./api` : ne pas appeler Gmail ni un serveur réel.
Privilégier les sélecteurs accessibles (`getByRole`, `getByLabelText`) et tester les actions
utilisateur, les erreurs, les confirmations et l'absence de requêtes sensibles avant confirmation.
