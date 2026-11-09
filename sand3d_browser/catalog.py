"""Incremental read-only filename inventory, independent of bpy.

No asset is opened. Explicit local roots, mapped drives and UNC roots are supported.
Links and Windows junctions are excluded.
The caller controls iteration, cancellation and retention of the index.
"""
from dataclasses import dataclass
from pathlib import Path
import os
import stat
import fnmatch

IMAGE_FORMATS = frozenset({'.png','.jpg','.jpeg','.bmp','.tga','.tif','.tiff','.webp','.exr','.hdr'})
FORMATS = frozenset({".usda", ".usd", ".usdc", ".glb", ".gltf", ".obj",
                     ".stl", ".3mf", ".blend", ".fbx", ".dae"}) | IMAGE_FORMATS
SKIP_DIRECTORIES = frozenset({".git", ".cache", "__pycache__"})


def is_model_filename(name):
    """Do not mistake common compiled object files for Wavefront models."""
    lower = name.lower()
    if lower.endswith(('.c.obj', '.cc.obj', '.cpp.obj', '.cxx.obj', '.cu.obj', '.asm.obj')):
        return False
    return Path(name).suffix.lower() in FORMATS


@dataclass(frozen=True)
class Asset:
    relative_path: str
    format: str
    size: int


def is_link(path):
    info = os.lstat(path)
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400)


def local_root(value):
    """Validate the configured root, without listing shares or parent folders.

    Historical function name retained for compatibility. Access rights and
    availability are checked by normal filesystem calls, never network discovery.
    """
    if not value:
        raise ValueError("Choisissez un dossier absolu, local ou réseau.")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("Le chemin doit être absolu.")
    # Check only the selected folder, not each parent or the server/share root.
    if is_link(path):
        raise ValueError("Les liens et jonctions ne sont pas parcourus.")
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError("Le chemin ne désigne pas un dossier.")
    return path


def scan(value, recursive=True, excluded=()):
    """Yield (asset-or-None, warning-or-empty) per entry to allow UI yielding.

    A scandir handle may remain open between yields. Closing the generator
    releases it on cancellation. Sources are never modified.
    """
    root = local_root(value)
    # Lexical comparison only: never probe an excluded output directory.
    exclusions = tuple(os.path.normcase(os.path.abspath(p)) for p in excluded if p)
    def excluded_path(path):
        candidate = os.path.normcase(os.path.abspath(path))
        return any(candidate == p or candidate.startswith(p + os.sep) for p in exclusions)
    if excluded_path(root):
        yield None, 'Bibliothèque ignorée : dossier réservé aux assets préparés'
        return
    pending = [root]
    while pending:
        folder = pending.pop()
        try:
            if is_link(folder) or not folder.resolve().is_relative_to(root):
                yield None, "Dossier lié ignoré"
                continue
            with os.scandir(folder) as entries:
                for entry in entries:
                    try:
                        if excluded_path(entry.path):
                            yield None, ''
                        elif is_link(entry.path):
                            yield None, "Lien ignoré"
                        elif entry.is_dir(follow_symlinks=False):
                            if recursive and entry.name not in SKIP_DIRECTORIES:
                                pending.append(Path(entry.path))
                            yield None, ""
                        elif entry.is_file(follow_symlinks=False):
                            suffix = Path(entry.name).suffix.lower()
                            asset = None
                            if is_model_filename(entry.name):
                                asset = Asset(str(Path(entry.path).relative_to(root)),
                                              suffix[1:], entry.stat(follow_symlinks=False).st_size)
                            yield asset, ""
                        else:
                            yield None, ""
                    except OSError as exc:
                        yield None, f"Entrée inaccessible : {entry.name} — {exc.strerror}"
        except OSError as exc:
            yield None, f"Dossier inaccessible : {folder} — {exc.strerror}"


def search(assets, query=""):
    query=query.strip()
    if '*' in query or '?' in query:
        pattern=query.replace('\\','/').casefold()
        return [a for a in assets if fnmatch.fnmatchcase(
            (a.relative_path.replace('\\','/') if '/' in pattern else a.relative_path.replace('\\','/').rsplit('/',1)[-1]).casefold(), pattern)]
    words = query.casefold().split()
    return [a for a in assets if all(w in a.relative_path.casefold() for w in words)]
