# POWER IMPORTER — Roadmap

Last updated: 2026-11-09. This document distinguishes implemented local milestones from future intentions. Version numbers describe development builds; they do not imply that each build has already been published on GitHub.

## Origin and direction

Sand3D’s available collections prompted the initial idea: make those resources easier to organize and use in Blender. The scope expanded to include large existing MZERMARTS asset libraries without moving or renaming their folders, including local and network storage.

The long-term goal is to reduce repeated searching and preparation when building a scene or an object made of multiple parts. Users should be able to collect assets from different sources, prepare them consistently and reopen that preparation later.

## Implemented milestones

| Milestone | Delivered scope | Validation status |
|---|---|---|
| 0.1.0 | Configurable library folders, file inventory and search in the sidebar | Initial local prototype and isolated tests |
| 0.1.1 | Network-path support in the initial catalogue workflow | Local development milestone |
| 0.2.0 | USD import, model thumbnail preparation and reusable Blender assets | Isolated tests and user trials |
| 0.2.1 | Fix for stale registered result properties after upgrading | Upgrade fix and user trials |
| 0.5.0 | OBJ, STL and GLB/glTF imports alongside USD | Isolated tests and user trials |
| 0.5.1 | Missing-texture selection/omission and two configurable logs | Isolated tests and user trials |
| 0.6.0 | Wildcards, image actions, controlled standalone BLEND append, gallery and settings backup/restore | Isolated tests and user trials; external settings export confirmed by the user |
| 0.6.1 | Detailed list and two thumbnail sizes; pagination beyond 500; nested output exclusion | Isolated tests and user trials with prepared thumbnails |
| 0.7.0 | Dedicated workspace/window, explicit destination binding and gallery/sidebar separation | Implemented and tested in isolated Blender 5.0; user validation in progress |

See [CHANGELOG.md](CHANGELOG.md) for change details. Compatibility beyond the tested installation is not inferred from these milestones.

## Companion utility track — available

The Windows settings utility is a separate companion to the add-on, introduced alongside the 0.6 workflow. It exports/imports settings through file dialogs without opening Blender’s interface, using the selected installed Blender in background mode. A real saved-settings export has been confirmed by the user.

It supports workstation migration and distribution of a team-defined library configuration. Mapped drives and UNC shares are supported by the add-on, but paths and access rights must be suitable for every recipient. Library roots, prepared-output paths and both log paths are stored literally. No assets are copied, and no automatic deployment, path remapping or team synchronization is implemented.

The utility does not require a separate Python installation. It requires Blender, operates on saved preferences and must be used with interactive Blender sessions closed. Details: [SETTINGS_UTILITY.md](SETTINGS_UTILITY.md).

## Planned toward 1.0

The following work is planned, not available in 0.7. Ordering may change based on testing; no release dates are committed here.

### Multi-selection and reusable preparation sets

- Ctrl/Shift selection, checkboxes and selection of filtered results.
- A persistent basket that combines assets from different folders and libraries.
- Named preparation sets storing source references, chosen options and destinations.
- Explicit reporting of missing or moved sources when reopening a set.

### Batch operations and conversion

- Thumbnail and prepared-asset generation for selected files.
- Batch import into an explicitly selected scene.
- Direct conversion from the independent browser through isolated Blender workers, without changing the working Layout scene.
- Mixed input formats converted to a common chosen output format, where supported.
- One output file per asset by default; optional grouped collection or assembly, without silently merging mesh geometry.
- Per-file progress, errors and naming-collision handling; no silent overwrite of an existing file.

### Proposed export presets

| Preset family | Proposed output | Important options and validation |
|---|---|---|
| For Blender Scene | BLEND | Separate assets or grouped collection; packed textures; hierarchy preservation |
| For DAZ / Hexagon | OBJ + MTL | Preserve material-zone assignments even without textures; optional textures; destination-specific axes and scale |
| For Unreal Engine / Twinmotion | GLB / glTF | Textures and compatible materials; validate each target application separately |
| For 3D Print | STL or OBJ, with MTL when useful | Units, dimensions and mesh checks; material zones where supported by the destination |

Preset names are families of intended workflows, not guarantees that a format preserves every feature. MTL definitions and OBJ material assignments should be retained where requested; a slicer’s interpretation of those assignments must be validated separately.

### Print-preparation validation

- Investigate a mandatory analysis stage for the 3D Print preset using the installed 3D Print Toolbox, after verifying its actual version and callable operations.
- Distinguish analysis from geometry repair: repairs must be explicitly chosen and applied to a copy.
- Define clear warning and blocking criteria, with a report for each asset.
- Treat slicing, material, support and machine setup as separate steps; passing mesh checks alone does not guarantee printability.
- Consider 3MF only after validating a suitable integration; it is not an implemented export in the current add-on.

### Optional specialized adapters

- Investigate Diffeomorphic for native DAZ files and DazToBlender for properly structured bridge exports.
- Keep general OBJ/MTL export separate from specialized DAZ pose/morph return workflows.
- Current status: local source audit only; no completed DAZ round-trip integration is claimed.

## Additional directions under consideration

Favorites, download history, custom collections, richer PBR material workflows, supported-model parametric controls, Sand3D catalogue/download integration and compatibility testing for other Blender versions. These are candidates, not committed features of 1.0.

## Validation principles

Preserve original files, use explicit destinations, keep libraries in place, separate reusable core code from application adapters and report format limitations. Test source-to-output round trips where relevant: scale, axes, material zones, UVs, textures, hierarchy and editability.
