"""Executed only by a separate, isolated Blender process."""
import sys
import json
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
from sand3d_browser.model_io import import_model


def prepare(root, relative, output, unitless_scale=1.0, options_json='{}'):
    output = Path(output)
    if output.with_suffix('.blend').exists() or output.with_suffix('.png').exists():
        raise ValueError('Destination existante ; aucun remplacement automatique')
    options = json.loads(options_json)
    collection, objects = import_model(bpy.context, root, relative, float(unitless_scale),
        options.get('replacements', {}), options.get('omit', False))
    for obj in bpy.context.scene.objects:
        if obj not in objects:
            obj.hide_render = True
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(p) for o in objects if o.type == 'MESH' for p in o.bound_box]
    if not points:
        raise ValueError('Pas de maillage pour la miniature')
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) / 2
    collection.instance_offset = center
    extent = max((high - low).length, 0.001)
    camera_data = bpy.data.cameras.new('Sand3D aperçu')
    camera = bpy.data.objects.new('Sand3D aperçu', camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + Vector((1, -1.4, 1)) * extent
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = extent * 1.15
    camera_data.clip_start = extent / 1000
    camera_data.clip_end = extent * 20
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(output.with_suffix('.png'))
    bpy.ops.render.render(write_still=True)
    collection.asset_mark()
    collection.asset_data.description = 'Source : ' + str(Path(root) / relative)
    # Set embedded preview pixels directly: avoid the OS-wide thumbnail cache.
    image = bpy.data.images.load(str(output.with_suffix('.png')), check_existing=False)
    preview = collection.preview_ensure()
    preview.image_size = tuple(image.size)
    preview.image_pixels_float = list(image.pixels)
    preview.is_image_custom = True
    # Full save retains embedded previews; libraries.write omits them in 5.0.
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')), check_existing=False)
    print('SAND3D_ASSET_READY', output)


if __name__ == '__main__':
    prepare(*sys.argv[sys.argv.index('--') + 1:])
