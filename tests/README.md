# Running the included tests

Use Blender 5.0 or specify a compatible installation explicitly. Tests create local fixtures and isolated profiles under test-artifacts. They retain diagnostics and do not clean up files automatically.

PowerShell:

```powershell
.\tests\run_blender.ps1 -Script blender_v06.py
.\tests\run_blender.ps1 -Script blender_v061.py
.\tests\run_blender.ps1 -Script blender_multiformat.py
.\tests\run_blender.ps1 -Script blender_recovery.py
```

GUI integration test with a standard Python installation:

```
python tests/run_gui.py blender_v07_ui.py
```

Specify Blender with -Blender for the PowerShell runner, or --blender for run_gui.py. The GUI runner opens a separate Blender instance, performs operations on generated test scenes, and closes that test instance. Never substitute a production profile for its isolated test environment.
