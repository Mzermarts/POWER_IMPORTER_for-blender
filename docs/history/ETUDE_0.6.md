# MZERMARTS Power Importer — étude de la version 0.6

Proposition, pas une version livrée. La version installable reste 0.5.1. L’étude et les tests n’ont pas modifié ses modules ni la session Blender de production.

## Orientation

Un navigateur commun pour modèles, images et matériaux, avec des actions adaptées au type sélectionné. Sand3D reste un fournisseur de catalogue parmi d’autres ; les bibliothèques historiques MZERMARTS restent utilisables à leur emplacement. Conserver les préférences de l’add-on et son identifiant technique lors d’un éventuel changement de nom public pour éviter une perte de configuration.

## Périmètre recommandé de la 0.6

1. Recherche avec jokers *, ?, *.obj, *.blend et motifs de noms, insensible à la casse ; mots simples conservés. Appliquer la recherche par Entrée ou bouton ; résultats, compteur et détail actualisés ensemble. Définir explicitement si un motif porte sur le nom ou un chemin : proposition nom par défaut, chemin relatif si le motif contient un séparateur.
2. Ajout natif depuis des .blend autonomes, sans ouvrir leur scène à la place du projet courant. Nouvelle collection, objets/hiérarchies/matériaux préservés. Les fichiers liés, ressources externes et mécanismes actifs doivent encore être traités et vérifiés avant intégration générale ; le test d’append autonome ne valide pas ces cas.
3. Catégorie Images, d’abord PNG et JPEG, puis autres formats décodés par Blender après validation. Grille de miniatures et aperçu agrandi de la sélection. Les images sont des ressources indépendantes, sans obligation de conversion en .blend pour les consulter.
4. Actions image : créer un matériau indépendant ; ajouter l’image à une copie du matériau choisi ; affecter sur le mesh actif ou les faces choisies selon un mode explicite ; importer en plan avec proportions et transparence ; charger dans l’éditeur d’images pour préparer le travail UV.
5. Distinguer les rôles couleur/alpha/roughness/normal : respecter les espaces colorimétriques et les nœuds nécessaires, ne pas changer silencieusement une image partagée. La création d’un matériau de couleur de base est différente de la construction automatique d’un matériau PBR complet.
6. Afficher la carte UV utilisée. Une image ne contient pas les coordonnées UV du mesh. Utiliser les UV existants ; proposer une nouvelle carte ou un dépliage seulement comme action séparée. Ne pas écraser le dépliage ni un matériau partagé ; isoler les données lorsque nécessaire pour ne toucher que la cible choisie.
7. Clarifier le dossier des copies Blender/miniatures, le bouton sans texture et l’état des deux journaux (désactivé/configuré non vérifié/écriture vérifiée/erreur).

## Aperçu au survol

Objectif pertinent : agrandir une vignette déjà disponible après un court survol. Ce comportement n’est pas encore implémenté ni validé graphiquement. Les API de grille de vignettes, d’icône agrandie et de dessin dans la vue 3D sont présentes dans Blender 5.0 ; cela ne prouve pas à lui seul un survol fiable dans une UIList défilante.

Le prototype graphique doit vérifier coordonnées des lignes, défilement, haute densité d’affichage, fermeture de fenêtre, changements de sélection et annulation. Ne pas importer ou rendre un modèle volumineux à chaque mouvement de souris. Lire une miniature existante ou en cache ; préparer les modèles 3D en arrière-plan et à la demande. Garder l’aperçu de sélection comme solution stable pendant la validation du survol.

## Tests réalisés

Script : tests/blender_v06_feasibility.py, via tests/run_blender.ps1, avec profil Blender isolé.

Blender 5.0.0 :

- Huit motifs de recherche vérifiés sur quatre noms témoins : *, *.obj, *.BLEND, room*, *rock*, images/*.png, r?ck.obj, notfound*.
- PNG 64×32 créé puis relu par Blender.
- Matériau à nœud Image Texture et liaison explicite à une carte UV existante ; conservation des anciens matériaux et coordonnées UV.
- Copie d’image dédiée au rôle Non-Color, sans changer l’espace de l’image couleur partagée.
- Opérateur natif image.import_as_mesh_planes exécuté : un plan, matériau et UV présents, rapport hauteur/largeur 0,5 conservé.
- Append natif d’une collection .blend autonome : scène courante et objets préexistants conservés.
- Présence de UILayout.template_icon_view, UILayout.template_icon et SpaceView3D.draw_handler_add vérifiée par RNA/API.

Limites : tests de faisabilité sur fichiers construits localement, pas des fonctionnalités intégrées à l’add-on. PNG testé ; JPEG et autres formats restent à vérifier. Pas de test graphique du survol, de génération d’UV automatique ou de montage PBR multi-images. Aucun fichier utilisateur n’a servi de témoin.

## Étapes suivantes

0.6 : parcours local cohérent, ajout .blend autonome contrôlé, consultation visuelle et quatre actions image explicites. Puis approfondir selon les retours : survol avancé, ensembles PBR, extraction de matériaux depuis .blend, favoris et traitements par lots. Le téléchargement Sand3D CAD reste une opération séparée avec sa destination à définir.

## Sources officielles

- https://docs.blender.org/api/5.0/bpy.types.UILayout.html
- https://docs.blender.org/api/5.0/bpy.types.SpaceView3D.html
- https://docs.blender.org/manual/en/5.0/render/shader_nodes/textures/image.html
- https://docs.blender.org/manual/en/5.0/modeling/meshes/import_images_as_planes.html
- https://docs.blender.org/api/5.0/bpy.types.BlendDataLibraries.html
