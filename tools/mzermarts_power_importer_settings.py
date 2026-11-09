"""Portable settings API and independent Blender script (no add-on imports).

Blender Text Editor: call export_settings(path) or import_settings(path).
CLI: blender --background --disable-autoexec --python <this-file> -- export file.json
Use import file.json --save-preferences to persist explicitly. No --factory-startup
on a production profile: it would replace unrelated preferences when saving.
"""
import json
import math
import ntpath
from pathlib import Path
import uuid

ADDON = 'sand3d_browser'
FIELDS = ('prepared_directory', 'general_log', 'error_log')


def validate(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('addon') != ADDON:
        raise ValueError('Fichier de réglages MZERMARTS Power Importer version 1 attendu')
    libraries = data.get('libraries')
    if not isinstance(libraries, list) or len(libraries) > 1000:
        raise ValueError('Liste de bibliothèques invalide')
    result = {'schema_version': 1, 'addon': ADDON, 'libraries': []}
    for row in libraries:
        if not isinstance(row, dict):
            raise ValueError('Bibliothèque invalide')
        entry = {}
        for name in ('name', 'directory'):
            value = row.get(name, '')
            if not isinstance(value, str) or '\x00' in value or len(value) > 4096:
                raise ValueError('Nom ou chemin invalide')
            entry[name] = value
        for name in ('enabled', 'recursive'):
            value = row.get(name, True)
            if not isinstance(value, bool):
                raise ValueError('Option de bibliothèque invalide')
            entry[name] = value
        value = row.get('unitless_scale', 1.0)
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or not 0.000001 <= value <= 1000000:
            raise ValueError('Échelle OBJ/STL invalide')
        entry['unitless_scale'] = float(value)
        result['libraries'].append(entry)
    for name in FIELDS:
        value = data.get(name, '')
        if not isinstance(value,str) or '\x00' in value or len(value)>4096:
            raise ValueError('Chemin de sortie invalide')
        result[name] = value
    return result


def snapshot(prefs):
    data = {'schema_version': 1, 'addon': ADDON,
            'libraries': [{name:getattr(lib,name) for name in
                ('name','directory','enabled','recursive','unitless_scale')} for lib in prefs.libraries]}
    data.update({name:getattr(prefs,name) for name in FIELDS})
    return validate(data)


def write(path, data, overwrite=False):
    data = validate(data)
    # JSON export is explicit, but do not replace a file without an explicit flag.
    with Path(path).open('w' if overwrite else 'x', encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


def read(path):
    if Path(path).stat().st_size > 10*1024*1024:
        raise ValueError('Fichier de réglages supérieur à 10 Mo')
    return validate(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def apply(prefs, data, merge=False):
    data = validate(data)  # Complete validation before any mutation.
    if not merge:
        prefs.libraries.clear()  # Configuration only, never source files.
    existing = {ntpath.normcase(ntpath.normpath(lib.directory)):lib for lib in prefs.libraries if lib.directory}
    for entry in data['libraries']:
        normalized = ntpath.normcase(ntpath.normpath(entry['directory']))
        lib = existing.get(normalized) if merge and entry['directory'] else None
        if lib is None:
            lib = prefs.libraries.add()
            lib.uid = uuid.uuid4().hex
        for name,value in entry.items():
            setattr(lib,name,value)
        if entry['directory']:
            existing[normalized] = lib
    for name in FIELDS:
        setattr(prefs,name,data[name])
    prefs.active_library = 0
    # No directory probes, log writes, indexing or network access here.


def active_preferences(create=True):
    """Usable even when the add-on is absent or disabled, using a tiny RNA schema."""
    import bpy
    addon = bpy.context.preferences.addons.get(ADDON)
    if addon is None and not create:
        raise ValueError('Aucun réglage existant pour cet add-on dans cette session')
    if addon is not None and addon.preferences is not None and hasattr(addon.preferences,'libraries'):
        return addon.preferences
    class MZSettingsLibrary(bpy.types.PropertyGroup):
        uid: bpy.props.StringProperty()
        name: bpy.props.StringProperty()
        directory: bpy.props.StringProperty()
        enabled: bpy.props.BoolProperty(default=True)
        recursive: bpy.props.BoolProperty(default=True)
        unitless_scale: bpy.props.FloatProperty(default=1.0,min=0.000001,max=1000000)
    class MZSettingsPreferences(bpy.types.AddonPreferences):
        bl_idname = ADDON
        libraries: bpy.props.CollectionProperty(type=MZSettingsLibrary)
        active_library: bpy.props.IntProperty()
        prepared_directory: bpy.props.StringProperty()
        general_log: bpy.props.StringProperty()
        error_log: bpy.props.StringProperty()
    bpy.utils.register_class(MZSettingsLibrary)
    bpy.utils.register_class(MZSettingsPreferences)
    addon = addon or bpy.context.preferences.addons.new()
    addon.module = ADDON
    return addon.preferences


def export_settings(path, overwrite=False):
    write(path, snapshot(active_preferences(create=False)), overwrite=overwrite)


def import_settings(path, merge=False, save_preferences=False):
    data = read(path)
    apply(active_preferences(), data, merge=merge)
    if save_preferences:
        import bpy
        bpy.ops.wm.save_userpref()


if __name__ == '__main__':
    import argparse
    import sys
    parser=argparse.ArgumentParser(description='Sauvegarder/restaurer uniquement les réglages Power Importer, sans indexation.')
    parser.add_argument('action',choices=('export','import','validate'))
    parser.add_argument('file')
    parser.add_argument('--merge',action='store_true')
    parser.add_argument('--overwrite',action='store_true')
    parser.add_argument('--save-preferences',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    if args.action=='validate':
        read(args.file)
    elif args.action=='export':
        export_settings(args.file,args.overwrite)
    else:
        import_settings(args.file,args.merge,args.save_preferences)
    print('Réglages :',args.action,'terminé. Aucun dossier de bibliothèque n’a été parcouru.')
