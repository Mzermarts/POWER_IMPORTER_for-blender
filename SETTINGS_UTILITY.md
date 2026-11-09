# Windows settings utility — backup, migration and team configurations

`MZERMARTS-PowerImporter-Reglages.exe` is a separate companion tool for POWER IMPORTER settings. It provides an ordinary Windows interface with file selectors; the Python helper is embedded in the executable.

## What “without opening Blender” means

You do not need to open Blender’s graphical interface or navigate its preferences. The utility starts the **selected installed Blender in background mode** to read or write the add-on settings. Blender must therefore be installed; no separate Python installation is required.

Save your work and Blender preferences, then close Blender before using the tool. It refuses to start an operation while a Blender process is running. This prevents an open session from subsequently overwriting the restored settings with its older in-memory configuration.

Export reads preferences already saved on disk. To export unsaved changes from an open Blender session, use the add-on’s own Export Settings button, or save the preferences and close Blender first. Export fails explicitly when no existing add-on configuration can be found; it does not invent an empty backup.

## What the JSON contains

| Setting | Included |
|---|---|
| Library display names and directory paths | Yes |
| Library activation and inclusion of subfolders | Yes |
| Per-library OBJ/STL scale | Yes |
| Prepared BLEND/thumbnail output folder | Yes |
| General and errors-only log file paths | Yes |
| Models, images, prepared assets or log contents | No |
| Catalogue index or session selection | No |
| Scene/window destination binding | No |
| Other Blender settings or installed add-ons | No |

Paths are stored as strings exactly as configured. The JSON can reveal internal folder/server names; distribute it through the team’s appropriate channel.

## Export a backup

1. Save your work and preferences in Blender, then close Blender.
2. Open the utility and browse to `blender.exe` for the intended version.
3. Select **Exporter vers un JSON…**, choose the destination folder and file name, and confirm replacement only if intended.
4. Wait for the success message. Keep the JSON with your configuration backups.

The utility does not upload the backup or contact GitHub. Its diagnostic output and embedded helper copy remain under the Windows temporary directory in `MZERMARTS-PowerImporter`, in a separate folder per operation. No automatic cleanup is performed.

## Restore on the same or another workstation

1. Install the intended Blender version and a compatible POWER IMPORTER add-on on the receiving workstation.
2. Save any work/preferences and close Blender there.
3. Copy the JSON to that workstation through your chosen transfer method.
4. Open the utility, select that workstation’s correct `blender.exe`, and select **Importer un JSON…**.
5. Choose merge or replacement, then confirm the restoration.
6. After success, open Blender and review the library, prepared-output and log paths.
7. Verify the chosen log destinations if needed, then index the libraries manually.

**Merge** keeps unrelated library entries and adds or updates entries matching imported paths. **Replace** replaces this add-on’s configuration. In both modes the prepared-output and log paths are restored from the JSON, so merge does not preserve local output/log settings automatically.

The import saves preferences for the selected Blender installation/profile. Choose the intended version carefully; this is not a whole-Blender preferences migration. Custom or portable profiles must be selected using the appropriate Blender environment; the utility does not offer a separate profile picker.

## Team leader workflow

A team leader can prepare a standard library configuration, give the entries useful names, enable the intended roots and set recursion/scales. Exporting a JSON provides a reusable configuration template for the rest of the team without requiring everyone to navigate the same setup manually.

Each user restores the template, checks local differences and indexes when ready. The team leader distributes configuration references, not copies of the library itself. Updated configurations can be distributed later, but this is an explicit import workflow: there is no background synchronization, remote administration or automatic update service.

Shared source libraries can remain centrally managed with read access for users. Prefer per-user or per-workstation prepared-output and log destinations unless the team has explicitly arranged shared writing. The utility does not coordinate concurrent writers or change permissions.

## Mapped drives, UNC shares and path names

POWER IMPORTER supports local directories, mapped network drives and UNC paths.

| Example | What must be consistent |
|---|---|
| `G:\StudioAssets\Props` | `G:` must exist on each workstation and map to the intended location |
| `\\asset-server\StudioAssets\Props` | The server/share must be reachable and the user must have the required permissions |
| `C:\Users\ArtistA\Prepared` | This is specific to one workstation/account and usually needs adjustment on another |

The importer does not translate drive letters, replace account names, create network mappings, provision credentials or grant access rights. A UNC path avoids dependence on a drive letter, but it does not remove server reachability or permission requirements. Different path aliases for the same folder are not guaranteed to merge as one entry.

Check prepared-output and both log destinations as well as the library roots. In particular, a team leader’s personal log path should not be assumed valid for every team member. The prepared-output folder must already exist. Restoring JSON does not validate the reachability of every referenced directory or start indexing; an offline path can be restored and checked later.

## Scope and current validation

The utility is Windows-specific. Its exported JSON is the same configuration format used by the add-on. Real export has been confirmed by the user; import/export logic and offline-path restoration have been exercised in isolated Blender tests. A complete multi-workstation/network deployment has not yet been certified.

The executable uses the chosen Blender’s normal profile with automatic script execution disabled. Other installed extensions may still have their own startup behavior; the utility is not an isolation layer for all third-party add-ons.

The utility’s sources accompany the add-on source distribution under `tools/`. Executable releases can be distributed separately from the Blender installation ZIP so users can choose whether to use the companion tool.
