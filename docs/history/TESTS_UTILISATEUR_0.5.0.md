# Bilan des essais utilisateur de la version 0.5.0

## Résultats communiqués pendant les tests

- Import STL du connecteur rj45 : réussi, un objet importé.
- Import OBJ des lettrages MASK-a-RAD / network : réussi, deux objets distincts et couleurs visibles. Cela ne constitue pas une certification de tous les matériaux ou de l’échelle physique.
- Import des témoins USD Omniverse spiky et torus : objets présents dans la scène sur la capture finale.
- Préparation de miniature : message générique « Choisissez un dossier absolu, local ou réseau ». L’examen du code identifie le dossier de préparation non renseigné comme cause possible ; le contenu de cette préférence dans la session utilisateur n’a pas été vérifié.
- Import d’un autre OBJ : texture « Final Fight Texture.jpg » introuvable ou référence ancienne non acceptée.

## Consultation directe de la session Blender

Lecture de l’historique visible dans l’éditeur Info de Blender 5.0.0 après le signal TEST FINI. Deux erreurs distinctes observées :

1. WinError 2 : fichier de texture non trouvé à l’emplacement référencé dans le partage de ressources DAZ.
2. « Ressource hors périmètre ou chemin non pris en charge » : ancienne référence absolue vers un répertoire temporaire DAZ/HexagonMaps.

Le deuxième message provient du contrôle des chemins de l’add-on ; il ne prouve pas l’absence du fichier sur le poste. Aucun accès à ces emplacements DAZ n’a été déclenché pour les rechercher. Aucun journal persistant de la session n’a été inventé ou reconstitué. L’éditeur Info a été remplacé temporairement à la place de la Timeline, puis la Timeline et sa hauteur ont été restaurées ; scène et fichiers utilisateur non modifiés.

## Réponses dans la version 0.5.1

- Choix avant import : sans les textures natives, ou localisation manuelle des fichiers via le navigateur Blender. Pas de recherche automatique dans les disques.
- Le sélecteur commence dans la bibliothèque courante et laisse l’utilisateur naviguer dans les volumes et dossiers. Seul le fichier choisi peut être utilisé hors de la bibliothèque, sans autoriser l’exploration de son dossier parent.
- Récupération des images de texture pour OBJ/MTL, glTF/GLB et USD avec couches liées simples. Les fichiers de géométrie ou buffers absents ne sont pas ignorés.
- Copies techniques de travail pour remplacer les chemins ou omettre les images. Les fichiers sources restent inchangés ; les copies et journaux ne sont pas supprimés automatiquement.
- Message explicite lorsque le dossier de préparation n’est pas défini.
- Deux destinations de journaux configurables : général et erreurs uniquement, écriture en ajout.

## Vérification du correctif

Blender 5.0.0, profils isolés : tests de récupération OBJ, glTF, GLB et USD à sous-couche ; choix d’une image hors bibliothèque de test ; import sans textures ; préparation isolée après relocalisation ; journaux séparés, erreurs avec trace, destinations inaccessibles ; préservation SHA-256 des sources OBJ/MTL.

Contrôle graphique dans un Blender de test distinct : dialogue, ouverture du sélecteur de fichiers et import sans texture. Ce Blender a été fermé après l’essai, sans intervenir dans la scène utilisateur. Régressions : multi-format, miniatures avec textures empaquetées, adaptation USD et mise à jour depuis 0.1.1.

Limites : témoins construits localement, pas une couverture de toutes les extensions de shaders ou des textures à motifs UDIM. Les journaux couvrent le flux de l’add-on, pas toutes les opérations de Blender et des autres extensions.
