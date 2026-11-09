# MZERMARTS Power Importer — 0.6.1

Version de développement pour Blender 5.0.0. Interface : Préférences > Add-ons et Vue 3D > N > Power Importer.

## Correctif 0.6.1 — navigation et dossier de préparation

Trois boutons ouvrent les modes Liste détaillée, Petites vignettes et Grandes vignettes. Ces modes sont aussi accessibles dans la galerie. La liste indique nom, format et taille ; le panneau de détail montre la bibliothèque et le chemin relatif. Les tailles viennent de l’index et sont actualisées lors d’une réindexation.

La limite globale à 500 est supprimée : 1 000 résultats par page par défaut, de 50 à 10 000. Les commandes Page et les flèches permettent d’atteindre tous les résultats. Dans la galerie, la molette parcourt les vues d’un lot puis passe au lot suivant/précédent. Recherche ou filtre modifié : retour à la première page. Les réglages de présentation restent propres à la session.

Le dossier des copies peut être un sous-dossier de la bibliothèque (comme MZERMARTS-selections). Son arborescence entière est exclue avant exploration lors de l’indexation. Le choix du dossier de sortie vide l’index et impose une nouvelle indexation. Il ne peut pas être égal à une racine de bibliothèque ni englober une bibliothèque. Utiliser la même notation de chemin (lecteur mappé ou UNC) pour le dossier et sa bibliothèque.

La préparation reste unitaire : pas de traitement par lots dans cette livraison. Les sources ne sont pas modifiées, le cache est réutilisé et le glisser-déposer reste celui de l’Asset Browser natif. Les formats non préparés gardent une étiquette de format jusqu’à création de l’aperçu.

Validation 0.6.1 : 6 001 résultats parcourus sans perte ni doublon, réduction par joker et changement de taille de page, géométrie et zones de sélection des trois modes, préparation réelle dans un sous-dossier exclu, conservation de la source par SHA256, réindexation sans fichiers générés. Régressions 0.6 et mise à jour depuis 0.1.1 réussies. Vue petites vignettes contrôlée graphiquement ; le contrôle interactif des autres modes a été interrompu par une impossibilité d’activer la fenêtre de test. Tests dans des profils isolés, aucune mise à jour du Blender de production.

## Nouveautés 0.6 et limites

- Galerie intégrée : miniatures et agrandissement au survol, clic pour sélectionner, molette pour changer de page, Échap pour fermer. Les images ont un aperçu direct ; les modèles nécessitent une préparation préalable. Aucun rendu 3D automatique au survol.
- BLEND : ajout des objets et collections dans la scène actuelle, sans ouvrir ni remplacer celle-ci. Les bibliothèques liées et les fichiers compressés en Zstandard sont refusés. Enregistrer une copie autonome non compressée depuis la version Blender appropriée ; conserver l’original. Les fichiers de version supérieure sont refusés. Les scripts embarqués ne sont pas exécutés ; drivers complexes et nœuds OSL importés sont neutralisés avec avertissement. Les animations, rigs et contraintes complexes ne sont pas tous certifiés.
- Images : créer un matériau indépendant, appliquer au mesh actif, ajouter un nœud dans une copie de son matériau, importer un plan ou ouvrir l’éditeur d’image. Couleur, rugosité, normale et canal alpha sont distingués. Les UV existantes sont préservées ; une image seule ne définit pas de jeu UV et aucun dépliage automatique n’est effectué. Appliquer concerne toutes les faces du mesh actif.
- Export/import des réglages JSON dans les préférences. Fusion des bibliothèques par chemin par défaut, ou remplacement explicite de la configuration. Les chemins de sortie du fichier importé sont restaurés dans les deux modes. Aucun asset, index, journal ou contenu de dossier n’est copié. Aucune indexation ni ouverture des destinations n’est déclenchée par la restauration. Vérifier ensuite les chemins puis indexer manuellement.
- Le statut des journaux distingue champs vides, configuration non vérifiée et vérification réussie dans la session.

Tests Blender 5.0.0 : import/préparation BLEND, conservation de scène et sources, jokers, images/matériaux/plans/UV, export/import JSON sans sondage des chemins, mise à jour depuis 0.1.1, régressions OBJ/STL/glTF et récupération USD/textures/journaux. Galerie contrôlée graphiquement avec des images synthétiques. Aucune installation dans votre Blender de production. Compatibilité 4.2 et 5.2 non certifiée.

Le script indépendant et son mode d’emploi sont livrés séparément : mzermarts_power_importer_settings.py et REGLAGES_0.6.md.

## Formats

| Format | Index | Import dans la scène | Miniature et asset Blender |
|---|---|---|---|
| USD / USDA / USDC | Oui | Oui | Oui |
| Wavefront OBJ + MTL | Oui | Oui | Oui |
| STL ASCII / binaire | Oui | Oui | Oui |
| GLB / glTF 2.0 | Oui | Oui | Oui |
| 3MF | Oui | Non, extension distincte nécessaire | Non |
| BLEND autonome non compressé / ancien gzip | Oui | Ajout dans une collection | Oui |
| Images PNG/JPEG/BMP/TGA/TIFF/WebP/EXR/HDR | Oui | Matériau, texture ou plan | Aperçu direct |
| FBX / DAE | Oui | Non dans cet add-on | Non |

OBJ/STL/glTF utilisent les importeurs livrés avec Blender 5.0 ; aucun paquet Python ou service externe n’est ajouté. Le 3MF n’a pas d’opérateur dans l’installation Blender 5.0 de référence. Une extension 3MF existe sur la plateforme Blender : https://extensions.blender.org/add-ons/threemf-io/ ; elle n’est ni installée ni appelée automatiquement. Son intégration éventuelle devra être auditée séparément.

## Installer ou mettre à jour

Enregistrer le travail en cours. Installer sand3d_browser-0.6.1.zip via Install from Disk dans les préférences Blender, puis activer l’add-on. Redémarrer Blender si d’anciens modules restent chargés. Le panneau doit afficher Bibliothèques 0.6.1. Réindexer après mise à jour pour reconstruire les résultats et exclure les anciens faux positifs. Les versions antérieures livrées en ZIP sont conservées pour restauration.

La mise à jour conserve normalement les chemins des préférences ; une désinstallation complète peut les réinitialiser : les noter avant cette opération. Ce prototype n’a pas été installé automatiquement dans vos préférences de production.

## Bibliothèques et recherche

Ajouter plusieurs dossiers professionnels autorisés, locaux, UNC ou lecteurs mappés. Choisir l’activation et l’inclusion des sous-dossiers pour chacun. L’indexation est manuelle, en lecture seule, et ne suit pas liens ou jonctions. Retirer une entrée ne supprime aucun fichier.

L’index reste en mémoire de session. La recherche porte sur les mots des noms/chemins, avec filtre par format. La recherche et le filtre actualisent les résultats en mémoire automatiquement. Les jokers * et ? sont acceptés : *.obj, *.blend, room*, *rock*. Sans joker, les mots sont recherchés dans le chemin relatif. Avec joker sans séparateur, le motif porte sur le nom du fichier. Résultats paginés : 1 000 par page par défaut, réglables de 50 à 10 000 ; aucune troncature globale à 500. Les noms de fichiers compilés connus (.cpp.obj, .c.obj, .cc.obj, .cxx.obj, .cu.obj, .asm.obj) sont ignorés sans ouvrir leur contenu ; d’autres fichiers portant abusivement .obj seront contrôlés au moment de l’import.

N’ajouter que des dossiers dont le périmètre est autorisé, sans données personnelles. Aucun inventaire des serveurs ou partages. Sur réseau lent, un appel disque peut retarder l’interface entre deux possibilités d’annulation. Les dossiers synchronisés peuvent déclencher leurs mécanismes habituels.

## Import dans la scène

Sélectionner un modèle, rester en mode Objet puis cliquer Importer dans la scène. Le clic droit dans la liste propose les mêmes commandes. Les formats non intégrés ont les commandes d’import et de préparation désactivées.

Les nouveaux objets sont regroupés dans une collection, avec conservation de la hiérarchie importée. Les objets existants restent présents. Le monde, la caméra active, les unités, la plage et la position temporelles sont préservés ; les importeurs OBJ/STL/glTF préservent aussi les FPS. Ctrl-Z utilise l’annulation native de l’opérateur Blender.

OBJ : matériaux MTL et textures relatives pris en compte. GLB/glTF : matériaux et images de l’importeur natif. Les nouvelles images externes sont intégrées au fichier préparé ; les images déjà présentes dans votre scène ne sont pas modifiées pour les empaqueter. Les limitations habituelles des formats et shaders restent applicables.

### Échelle OBJ/STL

Le réglage Échelle OBJ / STL est propre à chaque bibliothèque ; 1 conserve les coordonnées avec les conventions d’axes des importeurs natifs. Il ne s’applique pas à USD ou glTF.

OBJ et STL ne fournissent pas d’unité physique fiable. Exemple : pour des coordonnées exprimées en millimètres dans une scène où une unité Blender vaut un mètre, choisir 0,001. Si une unité Blender vaut déjà un millimètre, choisir 1. Vérifier les dimensions avant fabrication. Aucun profil d’imprimante n’est déclenché.

## Miniatures et glisser-déposer

1. Dans les préférences, définir Dossier des assets préparés : dossier existant autorisé, réservé aux sorties ; un sous-dossier de bibliothèque est accepté et exclu de l’indexation.
2. Sélectionner un modèle, puis Créer miniature et asset glissable.
3. Un Blender séparé et isolé réalise l’import, le rendu 256×256 et la création d’une collection marquée comme asset. La scène de travail courante reste disponible.
4. Ouvrir l’Asset Browser, choisir MZERMARTS Sand3D ou All Libraries, actualiser si nécessaire, puis glisser la vignette dans la vue 3D. Le clic droit natif y donne ses actions habituelles.

Le glisser-déposer provient de l’Asset Browser natif, pas des lignes du panneau N. Les miniatures Workbench montrent forme et couleurs de matériaux, sans reproduire fidèlement les textures et tous les shaders. Le .blend préparé comprend la scène de préparation ; seule la collection du modèle est marquée comme asset.

Le dossier préparé reçoit .blend, PNG, logs et profils isolés, conservés sans nettoyage automatique. Il est ajouté aux bibliothèques natives de Blender. Les chemins suivent le mode normal de sauvegarde des préférences Blender.

Le cache tient compte de la version de préparation, de l’échelle et des dates/tailles du modèle ainsi que de ses ressources OBJ/MTL/glTF détectées. Une copie existante complète est réutilisée au clic Préparer ; les miniatures du panneau se rechargent à cette occasion après redémarrage. Les ressources USD simples détectées font aussi partie de cette clé. Il ne s’agit pas d’une empreinte du contenu complet. Un échec de préparation laisse les fichiers de diagnostic en place, sans suppression automatique.

## Contrôle des ressources

Avant import, contrôle des fichiers liés. Références hors bibliothèque, URI réseau, chemins absolus, traversées de parent et liens sont refusés en accès automatique. Pour les images manquantes, une sélection manuelle explicite peut désigner un fichier hors bibliothèque. Les textures et buffers relatifs simples dans la bibliothèque sont admis ; les données glTF embarquées sont admises. Le JSON glTF ou le bloc JSON GLB est limité à 32 Mo pour ce contrôle.

Cette validation conservatrice peut refuser des fichiers pourtant valides, par exemple des matériaux MTL avec options non couvertes, un encodage autre qu’UTF-8 ou des chemins ../ même s’ils restent dans un dossier autorisé. Aucun téléchargement ni exécution du Python des assets. Les articulations USD ne sont pas automatiquement converties en mécanismes Blender.

## Validation et limites

Tests Blender 5.0.0 en processus séparé avec profil isolé :

- Index, configuration multi-dossiers, récursivité, filtres, doublons de racine et exclusion des fichiers compilés connus.
- Import réel OBJ avec MTL/texture, STL ASCII et binaire, GLB et glTF à buffer/image externes.
- Préservation des objets et réglages, multiplicateur STL, refus des ressources hors périmètre.
- Préparation par les opérateurs réels, cache réutilisé, réouverture des .blend avec miniatures intégrées et textures empaquetées.
- Régression USD et mise à jour simulée depuis 0.1.1 avec chemins préservés.

Les PNG témoins OBJ et glTF ont été contrôlés visuellement. Le geste de glisser-déposer et le clic droit n’ont pas fait l’objet d’un nouveau contrôle graphique pour cette livraison. Les tests utilisent des témoins construits localement, pas une certification de toute bibliothèque ou de tous les cas glTF (animations, squelettes, extensions). Compatibilité 4.2/5.2 à tester séparément.

Lanceur : tests/run_blender.ps1 -Script blender_multiformat.py. Autres scripts : blender_smoke.py, blender_assets.py, blender_actions.py, blender_upgrade.py. Les témoins sont conservés sous test-artifacts. blender_network_assets.py utilise uniquement le périmètre Omniverse explicitement autorisé dans la mission initiale ; ne pas le lancer ailleurs sans autorisation correspondante.

La désactivation libère l’index et arrête un éventuel worker sans effacer ses sorties. Elle ne supprime ni bibliothèque source ni entrée Asset Library native. Pas encore de téléchargement CAD, index Parquet Sand3D, favoris, édition paramétrique ou exports personnalisés.

## Architecture

catalog.py : inventaire/recherche indépendants de bpy. model_io.py : adaptateurs OBJ/STL/glTF et contrôle des dépendances. usd_io.py : adaptateur USD. blender_ui.py : préférences, filtres et panneau. actions.py : commandes, cache et worker. prepare_asset.py : préparation isolée. __init__.py : chargement et rafraîchissement des modules.

Références officielles :
- https://docs.blender.org/api/5.0/bpy.ops.wm.html
- https://docs.blender.org/api/5.0/bpy.ops.import_scene.html
- https://docs.blender.org/manual/en/5.0/files/import_export/stl.html
- https://docs.blender.org/manual/en/5.0/editors/asset_browser.html

## Correctif 0.6.1 — textures et journaux

Avant un import ou une préparation contenant des images absentes ou des références anciennes, le dialogue propose :

- Importer/préparer sans les textures natives : les couleurs et facteurs de matériaux sont conservés autant que le format le permet, sans images.
- Choisir le fichier… : navigateur de fichiers Blender, sans recherche préalable, avec navigation libre parmi volumes et dossiers. Choisir un fichier pour chaque image concernée, puis Continuer avec les fichiers choisis.
- Abandonner cette opération.

Ces commandes restent accessibles dans le panneau Sand3D si le dialogue est fermé. La sélection du modèle est revérifiée avant reprise. Les remplacements sont propres à l’opération ; ils ne réécrivent pas les fichiers originaux. Pour une utilisation durable, préparer un asset Blender qui conserve ses textures empaquetées.

La récupération utilise des copies techniques de l’OBJ/MTL, du glTF/GLB ou des couches USD, dans le profil du worker ou le dossier temporaire de Blender. Les textures choisies peuvent y être copiées pour préserver des chemins relatifs fiables. Les buffers glTF sont conservés ; un buffer de géométrie absent reste une erreur. Les sources et les copies intermédiaires sont conservées, sans nettoyage automatique.

### Deux journaux réglables dans les préférences

Dans Configurer les bibliothèques, renseigner deux fichiers distincts, par exemple sand3d_general.log et sand3d_erreurs.log, dans un dossier existant de votre choix. Les chemins locaux, lecteurs mappés et UNC sont acceptés. Le bouton Vérifier les chemins des journaux crée les fichiers si nécessaire, sans effacer les fichiers existants.

- Général : configuration des bibliothèques, indexation et anomalies, recherche, début/fin des imports et préparations, réutilisation du cache, sélection manuelle de textures et abandons.
- Erreurs uniquement : événements ERROR, message, contexte et trace Python lorsqu’une exception est disponible ; rapport du worker lors d’un échec de préparation.

Les deux fichiers sont du texte UTF-8 au format JSON par ligne, avec horodatage UTC, version de l’add-on, session et contexte. Le général contient aussi les erreurs. Aucun fichier n’est tronqué, envoyé ou purgé automatiquement. Champs vides : journal correspondant désactivé. Il s’agit des journaux de l’add-on, pas d’une interception globale de Blender ou des autres add-ons. Ils ne recréent pas les erreurs passées avant activation.

Si une destination est inaccessible, l’interface le signale et l’opération 3D reste indépendante de cet échec d’écriture. Les journaux peuvent contenir les chemins de vos ressources : choisir une destination adaptée.

### Tests supplémentaires

Lancer tests/run_blender.ps1 -Script blender_recovery.py pour les scénarios de récupération, de relocalisation et de journalisation. Le contrôle graphique séparé a confirmé le dialogue, le sélecteur et l’import sans texture. Le bilan des tests utilisateur de la 0.5.0 est conservé dans TESTS_UTILISATEUR_0.5.0.md.
