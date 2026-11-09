"""Two append-only JSON-lines journals, with explicit user-selected paths."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import traceback
import uuid

SESSION = uuid.uuid4().hex
LAST_ERROR = ''
VERSION = '0.7.0'


def validate_paths(general, errors):
    paths = []
    for value in (general, errors):
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute() or path.suffix.lower() not in {'.log', '.jsonl', '.txt'}:
            raise ValueError('Choisir un chemin absolu de journal .log, .jsonl ou .txt')
        if not path.parent.is_dir() or path.is_dir():
            raise ValueError('Le dossier du journal doit déjà exister')
        if path.is_symlink():
            raise ValueError('Le journal ne doit pas être un lien')
        paths.append(os.path.normcase(str(path.resolve())))
    if len(paths) == 2 and paths[0] == paths[1]:
        raise ValueError('Choisir deux fichiers distincts pour les journaux')


def emit(general, errors, level, event, *, exception=None, **details):
    """Logging failure must never replay or invalidate a completed import."""
    global LAST_ERROR
    record = dict(timestamp=datetime.now(timezone.utc).isoformat(), version=VERSION,
                  session=SESSION, level=level, event=event, **details)
    if exception is not None:
        record['exception'] = str(exception)
        record['traceback'] = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    try:
        validate_paths(general, errors)
        line = json.dumps(record, ensure_ascii=False) + '\n'
        for value in (general, errors if level == 'ERROR' else ''):
            if value:
                with Path(value).open('a', encoding='utf-8') as stream:
                    stream.write(line)
        LAST_ERROR = ''
        return True
    except (OSError, ValueError) as exc:
        LAST_ERROR = str(exc)
        print('Sand3D journal inaccessible:', LAST_ERROR)
        return False


def event(context, level, name, exception=None, **details):
    import bpy
    addon = context.preferences.addons.get(__package__)
    if addon is None:
        return False
    prefs = addon.preferences
    return emit(prefs.general_log, prefs.error_log, level, name, exception=exception,
                blender=bpy.app.version_string, **details)
