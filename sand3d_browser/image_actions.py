"""Explicit image actions: independent material, active mesh, image plane, UV view."""
from pathlib import Path
import bpy
from .catalog import IMAGE_FORMATS, local_root
from .operation_log import event


def source(context):
    from .actions import selected
    from .model_io import scoped_path
    item=selected(context)
    root=local_root(item.root)
    path=scoped_path(root,root,item.relative_path)
    if path.suffix.lower() not in IMAGE_FORMATS:
        raise ValueError('Sélectionner un fichier image')
    return path


def load(path,role='COLOR'):
    image=bpy.data.images.load(str(path),check_existing=False)
    if not image.size[0] or not image.size[1]:
        raise ValueError('Image non décodable')
    image.colorspace_settings.name='sRGB' if role in {'COLOR','ALPHA'} else 'Non-Color'
    image.pack()
    return image


def make_material(path,role='COLOR',uv='',existing=None):
    mat=existing.copy() if existing else bpy.data.materials.new(path.stem)
    mat.name=path.stem+' — '+role
    mat.use_nodes=True
    tree=mat.node_tree
    shader=next((n for n in tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if shader is None:
        shader=tree.nodes.new('ShaderNodeBsdfPrincipled')
        out=next((n for n in tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or tree.nodes.new('ShaderNodeOutputMaterial')
        tree.links.new(shader.outputs['BSDF'],out.inputs['Surface'])
    tex=tree.nodes.new('ShaderNodeTexImage')
    tex.image=load(path,role)
    if uv:
        coordinates=tree.nodes.new('ShaderNodeUVMap')
        coordinates.uv_map=uv
        tree.links.new(coordinates.outputs['UV'],tex.inputs['Vector'])
    if role=='NORMAL':
        normal=tree.nodes.new('ShaderNodeNormalMap')
        tree.links.new(tex.outputs['Color'],normal.inputs['Color'])
        tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    else:
        socket={'COLOR':'Base Color','ROUGHNESS':'Roughness','ALPHA':'Alpha'}[role]
        tree.links.new(tex.outputs['Alpha' if role=='ALPHA' else 'Color'],shader.inputs[socket])
    mat['mzermarts_image_source']=str(path)
    return mat


class S3D_OT_image(bpy.types.Operator):
    bl_idname='sand3d.image_action'
    bl_label='Utiliser l’image'
    bl_options={'REGISTER','UNDO'}
    action: bpy.props.EnumProperty(items=[('MATERIAL','Créer un matériau',''),('APPLY','Appliquer au mesh actif',''),
        ('NODE','Copier le matériau actif et ajouter la texture',''),('PLANE','Importer en plan image',''),('EDITOR','Ouvrir dans l’éditeur image / UV','')])

    def execute(self, context):
        from .browser_windows import destination
        try:
            with destination(context) as target_context:
                return self.execute_in_destination(target_context)
        except ValueError as exc:
            event(context, 'ERROR', 'destination_invalid', exception=exc)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

    def execute_in_destination(self, context):
        try:
            state=context.window_manager.sand3d_state
            path=source(context)
            if self.action in {'APPLY','NODE'}:
                target=context.active_object
                if target is None or target.type!='MESH' or context.mode!='OBJECT':
                    raise ValueError('Choisir un mesh actif en mode Objet')
                uv=state.image_uv or (target.data.uv_layers.active.name if target.data.uv_layers.active else '')
                if uv and uv not in target.data.uv_layers:
                    raise ValueError('Carte UV choisie absente du mesh actif')
                if self.action=='NODE' and target.active_material is None:
                    raise ValueError('Le mesh actif n’a pas de matériau à copier')
                mat=make_material(path,state.image_role,uv,target.active_material if self.action=='NODE' else None)
                # Material slots and face assignments live on the mesh: isolate shared data.
                if target.data.users>1:
                    target.data=target.data.copy()
                if self.action=='NODE':
                    target.active_material=mat
                else:
                    target.data.materials.append(mat)
                    index=len(target.data.materials)-1
                    for face in target.data.polygons:
                        face.material_index=index
                    target.active_material_index=index
            elif self.action=='MATERIAL':
                mat=make_material(path,state.image_role)
                mat.use_fake_user=True
            elif self.action=='PLANE':
                if context.mode!='OBJECT':
                    raise ValueError('Passer en mode Objet avant de créer un plan')
                bpy.ops.image.import_as_mesh_planes(directory=str(path.parent),files=[{'name':path.name}],
                    overwrite_material=False,force_reload=False,image_sequence=False,use_transparency=True)
            else:
                if context.window is None:
                    raise ValueError('Éditeur graphique nécessaire')
                image=load(path)
                before=set(context.window_manager.windows)
                bpy.ops.wm.window_new()
                window=next(w for w in context.window_manager.windows if w not in before)
                area=max(window.screen.areas,key=lambda a:a.width*a.height)
                area.type='IMAGE_EDITOR'
                area.spaces.active.image=image
            state.status='Image utilisée : '+path.name+' — '+self.action
            event(context,'INFO','image_action_finished',action=self.action,source=str(path))
            return {'FINISHED'}
        except Exception as exc:
            event(context,'ERROR','image_action_failed',exception=exc,action=self.action)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


def draw(layout,context):
    state=context.window_manager.sand3d_state
    layout.prop(state,'image_role')
    obj=context.active_object
    if obj and obj.type=='MESH':
        layout.prop_search(state,'image_uv',obj.data,'uv_layers',text='Carte UV')
        if not obj.data.uv_layers:
            layout.label(text='Pas de carte UV : aucun dépliage automatique.')
    for action,label in [('MATERIAL','Créer un matériau indépendant'),('APPLY','Appliquer au mesh actif'),
                         ('NODE','Ajouter à une copie du matériau actif'),('PLANE','Créer un plan image'),('EDITOR','Ouvrir l’image / préparer les UV')]:
        layout.operator('sand3d.image_action',text=label).action=action


def register():
    bpy.utils.register_class(S3D_OT_image)


def unregister():
    bpy.utils.unregister_class(S3D_OT_image)
