"""USD imports restricted to the selected library; no remote asset resolver."""
from pathlib import Path
import re
import bpy
from .catalog import local_root, is_link


def checked_asset(root_value, relative, replacements=None, omit=False):
    from .model_io import scoped_path
    from .texture_recovery import usd_dependencies
    root = local_root(root_value)
    path = scoped_path(root, root, relative)
    if path.suffix.lower() not in {'.usd', '.usda', '.usdc'}:
        raise ValueError('Format USD attendu')
    return usd_dependencies(root, path, replacements, omit)[0]

def import_model(context, root, relative, replacements=None, omit=False):
    path = checked_asset(root, relative, replacements, omit)
    original_path = path
    if replacements or omit:
        from .texture_recovery import usd_copy
        path = usd_copy(path, local_root(root), replacements or {}, omit)
    before = set(bpy.data.objects)
    before_collections = set(bpy.data.collections)
    frame = (context.scene.frame_start, context.scene.frame_end, context.scene.frame_current)
    unit = context.scene.unit_settings.scale_length
    world = context.scene.world
    result = bpy.ops.wm.usd_import(
        filepath=str(path), create_collection=True, set_frame_range=False,
        import_cameras=False, import_lights=False, import_volumes=False,
        create_world_material=False, import_textures_mode='IMPORT_PACK',
        mtl_name_collision_mode='MAKE_UNIQUE', validate_meshes=True)
    context.scene.frame_start, context.scene.frame_end = frame[:2]
    context.scene.frame_set(frame[2])
    context.scene.unit_settings.scale_length = unit
    context.scene.world = world
    if result != {'FINISHED'}:
        raise RuntimeError('Import USD non terminé ; vérifier la scène avant de réessayer')
    objects = [o for o in bpy.data.objects if o not in before]
    if not objects:
        raise ValueError('Aucun objet importable dans ce fichier USD')
    # Wrapper retains all source transforms and enables native collection assets.
    collection = bpy.data.collections.new(original_path.stem)
    context.scene.collection.children.link(collection)
    imported_collections = set(bpy.data.collections) - before_collections - {collection}
    children = {child for parent in imported_collections for child in parent.children}
    for top in imported_collections - children:
        collection.children.link(top)
        if top.name in context.scene.collection.children:
            context.scene.collection.children.unlink(top)
    for obj in objects:
        if not any(owner in imported_collections for owner in obj.users_collection):
            collection.objects.link(obj)
            if obj.name in context.scene.collection.objects:
                context.scene.collection.objects.unlink(obj)
    collection['sand3d_source'] = str(original_path)
    collection['sand3d_library'] = root
    return collection, objects

