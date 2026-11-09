"""Recovery uses disposable copies; sources and their material files stay intact."""
from pathlib import Path
import os
import uuid
import json
import struct
import shutil
import re
from urllib.parse import unquote
import bpy


class MissingTextures(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__(f'{len(issues)} texture(s) absente(s) ou à relocaliser')


def token_key(owner, value):
    return str(owner) + '|' + value


def texture_path(root, owner, value, resolver, issues, replacements=None, omit=False):
    key = token_key(owner, value)
    replacement = (replacements or {}).get(key)
    if omit:
        return None
    if replacement:
        # Exactly the file selected by the user. No search, parent inventory,
        # or permission granted to other files in the selected volume.
        path = Path(replacement)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError('Le fichier de texture choisi est inaccessible')
        return path
    try:
        return resolver(root, owner.parent, value)
    except (OSError, ValueError) as exc:
        issues.append(dict(key=key, expected=value, owner=str(owner), reason=str(exc)))
        return None


def workspace():
    parent = Path(os.environ.get('BLENDER_USER_RESOURCES') or bpy.app.tempdir)
    folder = parent / 'w' / uuid.uuid4().hex[:12]
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def obj_copy(path, root, replacements, omit):
    """Rewrite only material references in a new OBJ and new MTL files."""
    from .model_io import words, scoped_path, texture_filename, dependencies
    dependencies(str(root), str(path.relative_to(root)), replacements=replacements, omit=omit)
    folder = workspace()
    materials = {}
    textures = {}

    def copy_mtl(source):
        if source in materials:
            return materials[source]
        target = folder / ('material_' + str(len(materials)) + '.mtl')
        output = []
        with source.open('r', encoding='utf-8-sig') as stream:
            for line in stream:
                parsed = texture_filename(line)
                if parsed is None:
                    output.append(line)
                elif not omit:
                    prefix, value = parsed
                    resolved = texture_path(root, source, value, scoped_path, [], replacements)
                    if resolved not in textures:
                        texture = folder / (f'texture_{len(textures)}' + resolved.suffix)
                        shutil.copyfile(resolved, texture)
                        textures[resolved] = texture.name
                    output.append(prefix + ' ' + textures[resolved] + '\n')
        target.write_text(''.join(output), encoding='utf-8')
        materials[source] = target.name
        return target.name

    output = []
    with path.open('r', encoding='utf-8-sig') as stream:
        for line in stream:
            parts = line.strip().split(maxsplit=1)
            if parts and parts[0] == 'mtllib' and len(parts) == 2:
                for value in words(parts[1]):
                    source = scoped_path(root, path.parent, value)
                    output.append('mtllib ' + copy_mtl(source) + '\n')
            else:
                output.append(line)
    implicit = path.with_suffix('.mtl')
    if implicit.exists() and implicit not in materials:
        source = scoped_path(root, path.parent, implicit.name)
        output.insert(0, 'mtllib ' + copy_mtl(source) + '\n')
    target = folder / path.name
    target.write_text(''.join(output), encoding='utf-8')
    return target


def gltf_copy(path, root, replacements, omit):
    from .model_io import dependencies, gltf_document, scoped_path
    dependencies(str(root), str(path.relative_to(root)), replacements=replacements, omit=omit)
    document = gltf_document(path)
    folder = workspace()
    for index, buffer in enumerate(document.get('buffers', [])):
        value = buffer.get('uri', '')
        if value and not value.startswith('data:'):
            source = scoped_path(root, path.parent, unquote(value))
            target = folder / f'buffer_{index}.bin'
            shutil.copyfile(source, target)
            buffer['uri'] = target.name
    if omit:
        # Retain material factors while dropping texture bindings, not geometry.
        pending = list(document.get('materials', []))
        while pending:
            node = pending.pop()
            if isinstance(node, dict):
                for name in list(node):
                    if name.endswith('Texture'):
                        del node[name]
                    elif isinstance(node[name], (dict, list)):
                        pending.append(node[name])
            elif isinstance(node, list):
                pending.extend(node)
        document.pop('images', None)
        document.pop('textures', None)
    else:
        for index, image in enumerate(document.get('images', [])):
            value = image.get('uri', '')
            if value and not value.startswith('data:'):
                source = texture_path(root, path, unquote(value), scoped_path, [], replacements)
                target = folder / (f'image_{index}' + source.suffix)
                shutil.copyfile(source, target)
                image['uri'] = target.name
    target = folder / path.name
    if path.suffix.lower() == '.gltf':
        target.write_text(json.dumps(document), encoding='utf-8')
    else:
        encoded = json.dumps(document).encode('utf-8')
        encoded += b' ' * (-len(encoded) % 4)
        with path.open('rb') as original, target.open('xb') as output:
            original.seek(12)
            old_size, kind = struct.unpack('<II', original.read(8))
            remaining = path.stat().st_size - 20 - old_size
            output.write(struct.pack('<4sIIII', b'glTF', 2, 20 + len(encoded) + remaining, len(encoded), kind))
            output.write(encoded)
            original.seek(20 + old_size)
            shutil.copyfileobj(original, output)
    return target


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.exr', '.hdr', '.bmp', '.tga', '.webp', '.dds'}


def usd_dependencies(root, path, replacements=None, omit=False):
    """Read individual Sdf layers without composing their external references."""
    from pxr import Sdf
    from .model_io import scoped_path
    pending, layers, resources, issues = [path], {}, {path}, []
    while pending:
        current = pending.pop()
        if current in layers:
            continue
        if len(layers) >= 256:
            raise ValueError('Trop de couches USD pour ce prototype')
        layer = Sdf.Layer.FindOrOpen(str(current))
        if layer is None:
            raise ValueError('Couche USD illisible')
        text = layer.ExportToString()
        resolved_tokens = {}
        for value in re.findall(r'@([^@]*)@', text):
            if not value:
                continue
            if Path(value).suffix.lower() in IMAGE_EXTENSIONS:
                resolved = texture_path(root, current, value, scoped_path, issues, replacements, omit)
            else:
                if '<' in value or '[' in value:
                    raise ValueError('Motif de ressource USD non pris en charge')
                resolved = scoped_path(root, current.parent, value)
            resolved_tokens[value] = resolved
            if resolved is not None:
                resources.add(resolved)
                if resolved.suffix.lower() in {'.usd', '.usda', '.usdc'}:
                    pending.append(resolved)
        layers[current] = (text, resolved_tokens)
    if issues:
        raise MissingTextures(list({issue['key']: issue for issue in issues}.values()))
    return path, resources, layers


def usd_copy(path, root, replacements, omit):
    _, _, layers = usd_dependencies(root, path, replacements, omit)
    folder = workspace()
    names = {source: f'layer_{index}.usda' for index, source in enumerate(layers)}
    copied = {}
    for source, (text, tokens) in layers.items():
        for value, resolved in tokens.items():
            if resolved is None:
                replacement = ''
            elif resolved in names:
                replacement = names[resolved]
            else:
                if resolved not in copied:
                    target = folder / (f'resource_{len(copied)}' + resolved.suffix)
                    shutil.copyfile(resolved, target)
                    copied[resolved] = target.name
                replacement = copied[resolved]
            text = text.replace('@' + value + '@', '@' + replacement + '@')
        (folder / names[source]).write_text(text, encoding='utf-8')
    return folder / names[path]
