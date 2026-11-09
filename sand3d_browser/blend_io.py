"""Append standalone .blend data without opening a scene or following libraries."""
from pathlib import Path
import gzip
import os
import struct
import bpy
from .catalog import local_root, is_link
from .texture_recovery import MissingTextures, token_key


def check_container(path):
    """Read block headers only, before native loading could resolve linked .blend files.

    Native 5.0 format: BLENDER17-01v0500, then code/SDNA/old/length/count.
    Legacy formats use the historical 12-byte header and 20/24-byte BHeads.
    """
    with path.open('rb') as raw:
        magic = raw.read(4)
    if magic == b'\x28\xb5\x2f\xfd':
        raise ValueError('Ce .blend est compressé Zstandard : enregistrer une copie non compressée dans Blender pour cette version')
    opener = gzip.open if magic[:2] == b'\x1f\x8b' else open
    with opener(path, 'rb') as stream:
        prefix = stream.read(12)
        if prefix.startswith(b'BLENDER17'):
            header = prefix + stream.read(5)
            if not header.startswith(b'BLENDER17-01v'):
                raise ValueError('En-tête .blend récent non pris en charge')
            version = int(header[13:17])
            layout = struct.Struct('<4sIQQQ')
            length_index = 3
        elif prefix.startswith(b'BLENDER') and prefix[7:8] in {b'-', b'_'}:
            version = int(prefix[9:12])
            endian = '<' if prefix[8:9] == b'v' else '>'
            layout = struct.Struct(endian + ('4sIQII' if prefix[7:8] == b'-' else '4sIIII'))
            length_index = 1
        else:
            raise ValueError('En-tête .blend invalide')
        if version > bpy.app.version[0]*100 + bpy.app.version[1]:
            raise ValueError('Fichier enregistré par un Blender plus récent ; utiliser une version compatible')
        for _ in range(2000000):
            raw_header = stream.read(layout.size)
            if len(raw_header) != layout.size:
                raise ValueError('Fichier .blend tronqué')
            values = layout.unpack(raw_header)
            code, size = values[0].rstrip(b'\0 '), values[length_index]
            if code == b'LI':
                raise ValueError('Ce .blend utilise des bibliothèques liées : préparer une copie autonome avec ses données locales avant import')
            if code == b'ENDB':
                return
            if size > 32*1024**3:
                raise ValueError('Bloc .blend de taille non prise en charge')
            stream.seek(size, 1)
    raise ValueError('Structure .blend non prise en charge')


def all_ids():
    result=set()
    for prop in bpy.data.bl_rna.properties:
        if prop.type == 'COLLECTION':
            result.update(item for item in getattr(bpy.data, prop.identifier) if isinstance(item,bpy.types.ID))
    return result


def external_path(root, source, value):
    from .model_io import scoped_path
    if value.startswith('//'):
        absolute = Path(bpy.path.abspath(value))
    else:
        absolute = Path(value)
        if not absolute.is_absolute():
            absolute = source.parent / absolute
    absolute = Path(os.path.normpath(str(absolute)))
    if not absolute.is_relative_to(root):
        raise ValueError('Ressource externe au dossier de bibliothèque')
    return scoped_path(root, root, str(absolute.relative_to(root)))


def append_model(context, root_value, relative, replacements=None, omit=False):
    from .model_io import scoped_path
    root = local_root(root_value)
    path = scoped_path(root,root,relative)
    check_container(path)
    if bpy.data.filepath and Path(bpy.data.filepath).resolve() == path:
        raise ValueError('Le fichier sélectionné est la scène ouverte ; choisir un fichier source distinct')
    before = all_ids()
    wrapper = None
    try:
        with bpy.data.libraries.load(str(path), link=False, reuse_local_id=False) as (src,dst):
            dst.collections = src.collections
            dst.objects = src.objects
        imported = all_ids() - before
        objects = [item for item in imported if isinstance(item,bpy.types.Object)]
        if not objects:
            raise ValueError('Ce .blend ne contient pas d’objet importable')
        images = [item for item in imported if isinstance(item,bpy.types.Image)]
        issues=[]
        image_paths={}
        for image in images:
            if image.packed_file or len(image.packed_files) or image.source in {'GENERATED','VIEWER'}:
                continue
            if image.source != 'FILE':
                raise ValueError('Image animée/UDIM non prise en charge dans ce premier import .blend')
            value=image.filepath
            if omit:
                continue
            replacement=(replacements or {}).get(token_key(path,value))
            try:
                if replacement:
                    candidate=Path(replacement)
                    if not candidate.is_absolute() or is_link(candidate) or not candidate.is_file():
                        raise ValueError('Texture choisie inaccessible')
                else:
                    candidate=external_path(root,path,value)
                image_paths[image]=candidate
            except (OSError,ValueError) as exc:
                issues.append(dict(key=token_key(path,value),expected=value,owner=str(path),reason=str(exc)))
        # Validate non-image dependencies before linking anything into the scene.
        other = imported - set(images)
        for owner, paths in bpy.data.file_path_map(subset=other, include_libraries=True).items():
            for value in paths:
                if not value or value.startswith('<builtin>'):
                    continue
                if isinstance(owner,bpy.types.Text):
                    continue  # Text content is not executed or reloaded.
                external_path(root,path,value)
        if issues:
            raise MissingTextures(issues)
        muted = 0
        for item in imported:
            animation=getattr(item,'animation_data',None)
            if animation:
                for curve in animation.drivers:
                    if curve.driver.type == 'SCRIPTED' and not curve.driver.is_simple_expression:
                        curve.mute=True
                        muted+=1
            if isinstance(item,bpy.types.Text):
                item.use_module=False
            if isinstance(item,bpy.types.NodeTree):
                for node in list(item.nodes):
                    if node.bl_idname == 'ShaderNodeScript':
                        node.mute=True
                    if omit and node.bl_idname == 'ShaderNodeTexImage':
                        item.nodes.remove(node)
        # Embedded material node trees may not be separate top-level IDs.
        for mat in [i for i in imported if isinstance(i,bpy.types.Material) and i.node_tree]:
            for node in list(mat.node_tree.nodes):
                if node.bl_idname == 'ShaderNodeScript':
                    node.mute=True
                if omit and node.bl_idname == 'ShaderNodeTexImage':
                    mat.node_tree.nodes.remove(node)
        for image,candidate in image_paths.items():
            image.filepath=str(candidate)
            image.reload()
            image.pack()
        collections={item for item in imported if isinstance(item,bpy.types.Collection)}
        children={child for owner in collections for child in owner.children}
        wrapper=bpy.data.collections.new(path.stem)
        for top in collections-children:
            wrapper.children.link(top)
        for obj in objects:
            if not any(owner in collections for owner in obj.users_collection):
                wrapper.objects.link(obj)
        wrapper['sand3d_source']=str(path)
        wrapper['sand3d_library']=root_value
        wrapper['sand3d_muted_complex_drivers']=muted
        context.scene.collection.children.link(wrapper)
        return wrapper,objects
    except Exception:
        # Only data created by this attempt are rolled back; no source file deletion.
        bpy.data.batch_remove(ids=all_ids()-before)
        raise
