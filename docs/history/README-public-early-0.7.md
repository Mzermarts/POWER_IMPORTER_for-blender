# MZERMARTS Power Importer — Blender add-on 0.7.0

Navigateur local de modèles et d’images pour Blender : bibliothèques configurables, recherche, aperçus, import et préparation d’assets. Issu du projet Sand3D Asset Browser ; aucun téléchargement de catalogue Sand3D n’est intégré à cette version.

## Installation

Version testée : Blender 5.0.0 sous Windows. Les versions 4.2 et 5.2 ne sont pas certifiées. Aucune dépendance Python supplémentaire à installer.

1. Sauvegarder le travail et exporter les réglages de l’add-on existant si nécessaire.
2. Installer `sand3d_browser-0.7.0.zip` depuis les préférences Blender, via Install from Disk.
3. Activer **MZERMARTS Power Importer**. Le panneau se trouve dans Vue 3D > N > Power Importer.
4. Ajouter les dossiers autorisés puis lancer manuellement l’indexation.

Le module conserve son identifiant `sand3d_browser` et le schéma JSON de réglages de la 0.6. Ne pas installer une seconde copie sous un autre nom. Les archives précédentes permettent un retour à une version antérieure ; réimporter une sauvegarde JSON si la configuration a été réinitialisée.

## Nouveauté 0.7 : onglet ou fenêtre

Depuis le panneau de la scène de travail, cliquer **Onglet** ou **Fenêtre**. La destination est mémorisée : fenêtre d’origine, scène et View Layer. Le navigateur partage la recherche, l’index et la sélection de la session. Son ouverture ne lance ni indexation ni import.

**Onglet** crée ou réutilise l’espace de travail Power Importer, construit avec des éditeurs Blender existants. **Fenêtre** ouvre une fenêtre principale indépendante et agrandit sa vue de navigation. Le panneau de commandes reste disponible à droite ; Échap ferme la galerie. Les boutons Liste/Petites/Grandes la rouvrent.

Le libellé **Destination** indique la scène qui recevra les modèles et les actions sur le mesh actif. Changer la scène affichée dans le navigateur ne redirige pas les imports. Si la destination est fermée, ou si sa scène ou son View Layer change, l’opération est refusée : retourner au Layout voulu et cliquer **Utiliser cette scène comme destination**. Aucun basculement silencieux vers une autre scène.

La destination n’est pas sauvegardée dans le JSON ni restaurée automatiquement après un redémarrage. Un workspace enregistré dans un fichier Blender devra donc être associé à nouveau à une destination dans la nouvelle session. Les fenêtres et workspaces sont des éléments natifs ; la désactivation de l’add-on les laisse ouverts au lieu de fermer une interface qui pourrait contenir du travail.

## Bibliothèques, affichage et formats

- Dossiers locaux, lecteurs mappés et chemins UNC ; sous-dossiers optionnels ; liens/jonctions ignorés.
- Recherche de mots ou jokers `*.obj`, `room*`, `*rock*`, `?` ; filtres par format.
- Pagination : 1 000 résultats par défaut, de 50 à 10 000 par page.
- Liste détaillée, petites/grandes vignettes, aperçu au survol. Les images sont prévisualisées directement ; les modèles nécessitent une préparation préalable. Une galerie active à la fois.
- Imports : USD/USDA/USDC, OBJ/MTL, STL, GLB/glTF et BLEND autonome compatible.
- Images : PNG/JPEG/BMP/TGA/TIFF/WebP/EXR/HDR selon décodage Blender ; matériau indépendant, application au mesh actif, copie de matériau avec texture, plan image ou éditeur d’image. Les UV existantes sont conservées ; aucun dépliage automatique.
- 3MF, FBX et DAE : inventaire seulement dans cette version.

Les BLEND compressés en Zstandard, ceux de version supérieure et les bibliothèques BLEND liées sont refusés. Utiliser une copie autonome non compressée compatible en conservant l’original. Scripts embarqués non exécutés ; drivers complexes et nœuds OSL importés neutralisés. Les rigs/animations complexes ne sont pas tous validés.

OBJ/STL : vérifier les unités et l’échelle par bibliothèque. Les formats et shaders n’ont pas tous les mêmes capacités de conservation des matériaux.

## Préparation et ressources

Choisir un dossier existant pour les copies Blender et miniatures. Un sous-dossier de bibliothèque est accepté et exclu de l’index ; il ne doit pas contenir une racine de bibliothèque. Son changement invalide l’index. Réindexer ensuite.

La commande de préparation lance un Blender isolé, produit une copie BLEND, un PNG et un diagnostic. Le cache complet est réutilisé. Le glisser-déposer passe par l’Asset Browser natif après préparation ; aucun glisser-déposer natif depuis les cartes de notre galerie. Les miniatures Workbench ne reproduisent pas tous les shaders.

Les textures manquantes peuvent être choisies manuellement dans un sélecteur, ou omises. Aucun balayage automatique de tous les disques. Les ressources liées sont contrôlées par les adaptateurs ; choisir uniquement des racines auxquelles on est autorisé à accéder. Les sources ne sont pas réécrites. Les fichiers intermédiaires et diagnostics sont conservés sans nettoyage automatique.

## Réglages et journaux

Exporter/importer les réglages JSON depuis les préférences, en fusionnant ou remplaçant la configuration. Cela ne copie ni assets ni logs, et ne lance pas d’indexation. Le script autonome `mzermarts_power_importer_settings.py` offre les mêmes fonctions depuis Blender.

Deux journaux configurables, UTF-8 JSON par ligne : général et erreurs. Écriture en ajout ; aucun effacement automatique. Le bouton de vérification teste les destinations choisies. Champs vides : journal correspondant désactivé. Les journaux peuvent inclure les chemins des fichiers traités.

## Développement et validation

Le cœur Python `catalog.py` est indépendant de bpy ; les imports sont séparés par adaptateurs ; `browser_windows.py` gère le contexte de destination ; `gallery.py` gère la navigation visuelle. Aucun code d’add-on DAZ tiers n’est inclus.

Tests avec témoins générés localement et profils Blender isolés :

```powershell
.\tests\run_blender.ps1 -Script blender_v06.py
.\tests\run_blender.ps1 -Script blender_v061.py
.\tests\run_blender.ps1 -Script blender_multiformat.py
.\tests\run_blender.ps1 -Script blender_recovery.py
python tests/run_gui.py blender_v07_ui.py
```

Adapter le chemin Blender avec `-Blender` pour le lanceur PowerShell ou `--blender` pour le lanceur GUI. Les tests créent des témoins et diagnostics sous `test-artifacts`, sans les supprimer. Le test de migration historique n’est pas inclus dans cette archive source car il dépend d’une ancienne livraison distincte.

Les tests GUI vérifient les imports vers la scène source malgré une autre scène dans le navigateur, les matériaux sur le mesh cible, le refus après changement/fermeture de destination, la réutilisation du workspace et le calcul d’espace devant le panneau N. Un contrôle visuel a été fait sur une capture du navigateur de test. Ces essais ne certifient pas toutes les bibliothèques ni toutes les configurations Blender.

## Suite du projet

Multisélection, paniers persistants, génération par lots et presets d’export/conversion sont prévus pour les prochains jalons vers 1.0 ; ils ne sont pas livrés dans cette version. Les intégrations DAZ restent au stade d’audit.

## Publication et licence

Cette archive fournit les sources et la documentation sans réglages utilisateurs, bibliothèques, logs, diagnostics ni binaires de test. Aucun dépôt n’est créé et rien n’est publié automatiquement. Le choix final de licence appartient au mainteneur ; aucun fichier LICENSE n’a été ajouté par cette livraison. Les ressources importées conservent leurs licences propres.
