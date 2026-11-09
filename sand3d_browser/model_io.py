"""Native format adapters and bounded dependency validation for Blender 5.0."""
from pathlib import Path
import json
import re
import struct
from urllib.parse import unquote
import bpy
from .catalog import local_root, is_link, is_model_filename
from . import usd_io
from .texture_recovery import MissingTextures, texture_path

SUPPORTED = frozenset({'usd', 'usda', 'usdc', 'obj', 'stl', 'glb', 'gltf', 'blend'})


def scoped_path(root, parent, value):
    """Check syntax before any file access; never follow links out of scope."""
    rel = Path(value)
    if not value or rel.is_absolute() or '..' in rel.parts or ':' in value:
        raise ValueError(f'Ressource hors périmètre ou chemin non pris en charge : {value}')
    candidate = parent / rel
    if not candidate.is_relative_to(root):
        raise ValueError('Ressource hors bibliothèque')
    for part in (candidate, *candidate.parents):
        if part == root:
            break
        if is_link(part):
            raise ValueError('Les ressources liées ne sont pas suivies')
    candidate = candidate.resolve(strict=True)
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError('Ressource hors bibliothèque ou non lisible')
    return candidate


def words(text):
    return [part.strip('"\'') for part in re.findall(r'"[^"]*"|\'[^\']*\'|\S+', text)]


def texture_filename(line):
    tokens = words(line.strip())
    if not tokens or tokens[0].startswith('#'):
        return None
    command = tokens.pop(0)
    if not (command.lower().startswith('map_') or command.lower() in {'bump', 'disp', 'decal', 'refl', 'norm'}):
        return None
    prefix = [command]
    while tokens and tokens[0].startswith('-'):
        option = tokens.pop(0).lower()
        prefix.append(option)
        if option in {'-o', '-s', '-t'}:
            count = 0
            while tokens and count < 3:
                try:
                    float(tokens[0])
                except ValueError:
                    break
                prefix.append(tokens.pop(0))
                count += 1
            if not count:
                raise ValueError('Option MTL sans valeur')
        else:
            count = 2 if option == '-mm' else 1
            if option not in {'-mm', '-blendu', '-blendv', '-boost', '-texres', '-clamp', '-bm', '-imfchan', '-type', '-colorspace'}:
                raise ValueError(f'Option de texture MTL non prise en charge : {option}')
            if len(tokens) < count:
                raise ValueError('Option MTL incomplète')
            prefix.extend(tokens[:count])
            tokens = tokens[count:]
    return (' '.join(prefix), ' '.join(tokens)) if tokens else None


def mtl_dependencies(root, mtl, issues, replacements=None, omit=False):
    paths = {mtl}
    with mtl.open('r', encoding='utf-8-sig', errors='strict') as stream:
        for line in stream:
            parsed = texture_filename(line)
            if parsed:
                resolved = texture_path(root, mtl, parsed[1], scoped_path, issues, replacements, omit)
                if resolved:
                    paths.add(resolved)
    return paths


def gltf_document(path):
    if path.suffix.lower() == '.gltf':
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Document glTF JSON supérieur à 32 Mo : contrôle manuel nécessaire')
        return json.loads(path.read_text(encoding='utf-8-sig'))
    with path.open('rb') as stream:
        header = stream.read(20)
        if len(header) != 20:
            raise ValueError('GLB tronqué')
        magic, version, total, size, kind = struct.unpack('<4sIIII', header)
        if magic != b'glTF' or version != 2 or kind != 0x4E4F534A or size > 32 * 1024 * 1024:
            raise ValueError('En-tête GLB non pris en charge')
        if total != path.stat().st_size or size > total - 20:
            raise ValueError('Taille GLB incohérente')
        return json.loads(stream.read(size).decode('utf-8'))


def dependencies(root_value, relative, replacements=None, omit=False):
    root = local_root(root_value)
    path = scoped_path(root, root, relative)
    extension = path.suffix.lower()[1:]
    if extension == '3mf':
        raise ValueError('3MF : nécessite une extension Blender distincte ; import non intégré à la version 0.5')
    if extension not in SUPPORTED or not is_model_filename(path.name):
        raise ValueError('Format non importable ou fichier compilé exclu')
    paths = {path}
    issues = []
    if extension == 'blend':
        from .blend_io import check_container
        check_container(path)
    elif extension in {'usd', 'usda', 'usdc'}:
        from .texture_recovery import usd_dependencies
        paths.update(usd_dependencies(root, path, replacements, omit)[1])
    elif extension == 'obj':
        has_vertex = False
        with path.open('r', encoding='utf-8-sig', errors='strict') as stream:
            for line in stream:
                if '\x00' in line:
                    raise ValueError('Fichier OBJ binaire : ce n’est pas un modèle Wavefront')
                parts = line.strip().split(maxsplit=1)
                if not parts:
                    continue
                if parts[0] == 'v':
                    has_vertex = True
                if parts[0] == 'mtllib' and len(parts) == 2:
                    for name in words(parts[1]):
                        paths.update(mtl_dependencies(root, scoped_path(root, path.parent, name), issues, replacements, omit))
        if not has_vertex:
            raise ValueError('Aucun sommet Wavefront dans ce fichier OBJ')
        # Some importers look for a same-name MTL even without mtllib.
        sidecar = path.with_suffix('.mtl')
        if sidecar.exists():
            paths.update(mtl_dependencies(root, scoped_path(root, path.parent, sidecar.name), issues, replacements, omit))
    elif extension in {'glb', 'gltf'}:
        document = gltf_document(path)
        if not isinstance(document, dict) or document.get('asset', {}).get('version') != '2.0':
            raise ValueError('Seul glTF 2.0 est pris en charge')
        pending = [document]
        image_nodes = {id(image) for image in document.get('images', [])}
        while pending:
            node = pending.pop()
            if isinstance(node, list):
                pending.extend(node)
            elif isinstance(node, dict):
                for name, value in node.items():
                    if name == 'uri' and isinstance(value, str):
                        if not value.lower().startswith('data:'):
                            if id(node) in image_nodes:
                                resolved = texture_path(root, path, unquote(value), scoped_path, issues, replacements, omit)
                                if resolved:
                                    paths.add(resolved)
                            else:
                                paths.add(scoped_path(root, path.parent, unquote(value)))
                    elif isinstance(value, (dict, list)):
                        pending.append(value)
    if issues:
        unique = {issue['key']: issue for issue in issues}
        raise MissingTextures(list(unique.values()))
    return path, paths


def checked_asset(root_value, relative):
    return dependencies(root_value, relative)[0]


def import_model(context, root, relative, unitless_scale=1.0, replacements=None, omit=False):
    path = dependencies(root, relative, replacements, omit)[0]
    original_path = path
    extension = path.suffix.lower()[1:]
    if extension == 'blend':
        from .blend_io import append_model
        return append_model(context,root,relative,replacements,omit)
    if extension in {'usd', 'usda', 'usdc'}:
        return usd_io.import_model(context, root, relative, replacements, omit)
    if replacements or omit:
        from .texture_recovery import obj_copy, gltf_copy
        if extension == 'obj':
            path = obj_copy(path, local_root(root), replacements or {}, omit)
        elif extension in {'glb', 'gltf'}:
            path = gltf_copy(path, local_root(root), replacements or {}, omit)
    before = set(bpy.data.objects)
    old_images = set(bpy.data.images)
    old_collections = set(bpy.data.collections)
    scene = context.scene
    frame = (scene.frame_start, scene.frame_end, scene.frame_current)
    settings = (scene.unit_settings.system, scene.unit_settings.scale_length,
                scene.camera, scene.world, scene.render.fps, scene.render.fps_base)
    try:
        if extension == 'obj':
            result = bpy.ops.wm.obj_import(filepath=str(path), global_scale=unitless_scale,
                validate_meshes=True, mtl_name_collision_mode='MAKE_UNIQUE')
        elif extension == 'stl':
            result = bpy.ops.wm.stl_import(filepath=str(path), global_scale=unitless_scale,
                use_scene_unit=False, use_mesh_validate=True)
        else:
            result = bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True,
                import_scene_extras=False, import_scene_as_collection=True)
    finally:
        scene.frame_start, scene.frame_end = frame[:2]
        scene.frame_set(frame[2])
        (scene.unit_settings.system, scene.unit_settings.scale_length, scene.camera,
         scene.world, scene.render.fps, scene.render.fps_base) = settings
    if result != {'FINISHED'}:
        raise RuntimeError('Import non terminé ; vérifier la scène avant de réessayer')
    objects = [o for o in bpy.data.objects if o not in before]
    if not objects:
        raise ValueError('Aucun objet importable dans ce fichier')
    for image in set(bpy.data.images) - old_images:
        if image.source == 'FILE' and not image.packed_file:
            image.pack()
    collection = bpy.data.collections.new(path.stem)
    scene.collection.children.link(collection)
    imported = set(bpy.data.collections) - old_collections - {collection}
    children = {child for owner in imported for child in owner.children}
    for top in imported - children:
        collection.children.link(top)
        if top.name in scene.collection.children:
            scene.collection.children.unlink(top)
    for obj in objects:
        if not any(owner in imported for owner in obj.users_collection):
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            collection.objects.link(obj)
    collection['sand3d_source'] = str(original_path)
    collection['sand3d_library'] = root
    collection['sand3d_unitless_scale'] = unitless_scale
    return collection, objects
