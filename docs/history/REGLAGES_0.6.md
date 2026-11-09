# Export et restauration des réglages — Power Importer 0.6

## Depuis Blender

Préférences > Add-ons > MZERMARTS Power Importer : **Exporter les réglages** capture les réglages courants dans un JSON choisi. **Importer les réglages** propose fusion (par défaut) ou remplacement. Le fichier entier est validé avant application. Le mode fusion conserve les bibliothèques existantes et ajoute/actualise celles de la sauvegarde ; les chemins des sorties sont restaurés depuis le JSON.

Le JSON contient les noms et chemins des bibliothèques, activation, sous-dossiers, échelles OBJ/STL, dossier des copies Blender et miniatures, et les deux chemins des journaux. Il ne contient aucun modèle, image, index ni contenu des logs. Les chemins sont stockés tels quels : adapter les lettres de lecteurs sur une autre machine. Ce fichier peut révéler vos chemins professionnels ; choisir sa destination en conséquence.

La restauration ne parcourt aucun dossier de bibliothèque et n’écrit pas dans les journaux. Les droits d’accès effectifs ne sont pas accordés par ce fichier. Après import, contrôler les chemins, vérifier les journaux si souhaité, puis lancer manuellement l’indexation. Sauvegarder les préférences selon le mode habituel de Blender.

## Script indépendant

`mzermarts_power_importer_settings.py` est autonome, sans import du package de l’add-on. Son export exige que des réglages existent déjà dans le profil ; il ne fabrique pas une sauvegarde vide. Il peut restaurer les réglages même si l’add-on est désactivé ou absent ; cela n’installe pas l’add-on.

Exemples PowerShell, à adapter aux emplacements choisis :

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' --background --disable-autoexec --python 'D:\Outils\mzermarts_power_importer_settings.py' -- export 'D:\Sauvegardes\power_importer.json'
& 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' --background --disable-autoexec --python 'D:\Outils\mzermarts_power_importer_settings.py' -- import 'D:\Sauvegardes\power_importer.json' --merge --save-preferences
```

L’export CLI lit les préférences déjà enregistrées sur disque ; pour les modifications encore en mémoire, utiliser le bouton d’export dans Blender. Ne pas exécuter une restauration persistante en parallèle d’un Blender susceptible de réenregistrer ses anciennes préférences : fermer d’abord cette session après sauvegarde du travail et de sa configuration. Ne pas ajouter `--factory-startup` à une restauration avec `--save-preferences`, car cela enregistrerait aussi les réglages par défaut d’autres fonctions Blender.

Sans `--save-preferences`, la restauration CLI reste limitée à la session lancée. Sans `--merge`, elle remplace la configuration de cet add-on. L’export refuse un fichier existant ; `--overwrite` permet explicitement son remplacement. Aucun fichier n’est supprimé automatiquement.

Validation seule avec un Python standard :

```powershell
python mzermarts_power_importer_settings.py validate power_importer.json
```

Pour restaurer une configuration précédente, réimporter son JSON. Les ZIP des versions antérieures restent disponibles ; aucune désinstallation ni réinstallation de production n’a été effectuée par ces tests.
