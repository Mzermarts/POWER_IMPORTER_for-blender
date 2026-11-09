# Utilitaire Windows — Réglages Power Importer

Double-cliquer MZERMARTS-PowerImporter-Reglages.exe. Aucun Python séparé à installer : le script est embarqué et exécuté par le Blender choisi.

1. Sauvegarder le travail et les préférences, puis fermer Blender.
2. Avec Parcourir, choisir blender.exe de la version concernée.
3. Exporter vers un JSON : choisir le dossier et le nom de la sauvegarde.
4. Importer un JSON : sélectionner la sauvegarde ; laisser Fusionner coché, ou le décocher pour remplacer la configuration de l’add-on. Confirmer la restauration.
5. Après succès, ouvrir Blender et contrôler les chemins avant d’indexer.

L’export lit les réglages déjà enregistrés, pas les changements non enregistrés d’une session. L’import enregistre les préférences du profil de la version sélectionnée. Il ne configure pas les partages réseau, ne copie pas les modèles et ne lance aucune indexation. Un profil portable ou personnalisé doit être utilisé selon les variables d’environnement Blender correspondantes ; l’outil ne choisit pas automatiquement un profil personnalisé.

L’exécutable lance Blender en arrière-plan avec --disable-autoexec. Le démarrage normal de Blender peut charger ses extensions et leurs propres mécanismes ; l’utilitaire n’offre pas d’isolation globale de ces composants. Il refuse de lancer une opération si Blender est déjà ouvert, pour éviter des écritures concurrentes des préférences.

Les fichiers techniques et le diagnostic restent dans le dossier temporaire Windows, sous MZERMARTS-PowerImporter, un sous-dossier par opération. Aucun nettoyage automatique. Le script Python est embarqué : pas besoin de le conserver à côté de l’exécutable.

Validation : compilation locale avec .NET Framework, autotest de construction de fenêtre, ressource Python embarquée et échappement des arguments. Le moteur Python a été testé dans les profils Blender 5.0 isolés de la version 0.6. Aucune restauration n’a été exécutée dans les préférences de production. Cet exécutable n’est pas signé numériquement.

Source : SettingsTool.cs. Reproduction depuis le dossier du projet :

```powershell
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /target:winexe /out:MZERMARTS-PowerImporter-Reglages.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /resource:mzermarts_power_importer_settings.py,settings.py SettingsTool.cs
```
