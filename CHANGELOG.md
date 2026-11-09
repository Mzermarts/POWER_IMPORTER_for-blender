# Changelog

## Documentation — 2026-11-09

- Documented the separate Windows settings utility, workstation migration and team-managed library configurations.
- Clarified background Blender execution, literal mapped/UNC paths, access rights, merge/replace behavior and workstation-specific output/log paths.
- No add-on or executable behavior changed.


## 0.7.0 — 2026-11-09

- Ajout des boutons Onglet et Fenêtre dans le panneau Power Importer.
- Espace de travail Power Importer réutilisable et fenêtre principale indépendante avec vue agrandie.
- Destination explicite : fenêtre, scène et View Layer mémorisés avant ouverture du navigateur.
- Routage des imports de modèles et actions sur les images vers la destination mémorisée.
- Refus de mutation si la fenêtre de destination est fermée, ou si sa scène ou son View Layer a changé.
- Galerie limitée à la largeur visible devant le panneau latéral ; message adapté aux petites zones.
- Arrêt de la galerie précédente lors du passage à une autre zone.
- Conservation des chemins, du format JSON de réglages et du module sand3d_browser pour les mises à jour.
- Tests GUI isolés de création/réutilisation de workspace, import entre scènes, matériaux, destinations invalides et désactivation.

## 0.6.1

- Modes liste détaillée, petites et grandes vignettes.
- Pagination réglable de 50 à 10 000 résultats, sans plafond global à 500.
- Dossier de préparation imbriqué accepté et exclu de l’indexation.

## 0.6.0

- Images, galerie, jokers et ajout de fichiers Blender autonomes compatibles.
- Export/import JSON des réglages et utilitaire Windows distinct.

## 0.5.1

- Choix manuel de textures manquantes ou import sans textures.
- Journaux général et erreurs configurables.

## 0.5.0

- OBJ, STL and GLB/glTF imports and asset preparation alongside USD.

## 0.2.1

- Upgrade fix for stale result RNA properties, including library identifiers.

## 0.2.0

- USD import, thumbnail preparation and reusable Blender collection assets.

## 0.1.1

- Network-path support for the initial library catalogue.

## 0.1.0

- Initial configurable-folder catalogue, indexing and search in the Blender sidebar.
