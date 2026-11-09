# Utilitaire de réglages Windows

Source WinForms : SettingsTool.cs. Le script de réglages est embarqué à la compilation ; il est exécuté par la version de Blender choisie dans la fenêtre. Il ne nécessite pas de Python séparé. Le binaire de cet outil est distinct de l’add-on et n’a pas été modifié par la 0.7.

Depuis ce dossier, compiler avec le compilateur C# .NET Framework, en référençant System.Windows.Forms.dll et System.Drawing.dll, cible winexe, et la ressource mzermarts_power_importer_settings.py sous le nom settings.py. Exemple d’arguments csc :

```
/target:winexe /out:MZERMARTS-PowerImporter-Reglages.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /resource:mzermarts_power_importer_settings.py,settings.py SettingsTool.cs
```

Fermer Blender après sauvegarde du travail et des préférences avant utilisation. L’export lit les préférences enregistrées ; l’import les enregistre explicitement pour la version sélectionnée. Les fichiers techniques restent dans le dossier temporaire Windows sous MZERMARTS-PowerImporter ; aucun nettoyage automatique. L’outil refuse une opération lorsqu’un processus Blender est déjà ouvert.
