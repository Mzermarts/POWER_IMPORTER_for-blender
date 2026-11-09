import bpy
from bpy_extras.io_utils import ImportHelper,ExportHelper
from . import settings_io


class S3D_OT_export_settings(bpy.types.Operator,ExportHelper):
    bl_idname='sand3d.export_settings'
    bl_label='Exporter les réglages'
    filename_ext='.json'
    filter_glob: bpy.props.StringProperty(default='*.json',options={'HIDDEN'})
    def execute(self,context):
        from .blender_ui import preferences
        try:
            settings_io.write(self.filepath,settings_io.snapshot(preferences(context)),overwrite=True)
            self.report({'INFO'},'Réglages exportés ; aucun asset copié')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


class S3D_OT_import_settings(bpy.types.Operator,ImportHelper):
    bl_idname='sand3d.import_settings'
    bl_label='Importer les réglages'
    filter_glob: bpy.props.StringProperty(default='*.json',options={'HIDDEN'})
    mode: bpy.props.EnumProperty(name='Restauration',items=[('MERGE','Fusionner les bibliothèques',''),('REPLACE','Remplacer la configuration','')],default='MERGE')
    def execute(self,context):
        from . import blender_ui,thumbnails
        if blender_ui.RUNNING:
            self.report({'WARNING'},'Arrêter l’indexation avant de restaurer les réglages')
            return {'CANCELLED'}
        try:
            data=settings_io.read(self.filepath)
            settings_io.apply(blender_ui.preferences(context),data,merge=self.mode=='MERGE')
            blender_ui.INDEX.clear()
            thumbnails.QUEUE.clear()
            context.window_manager.sand3d_state.results.clear()
            context.window_manager.sand3d_state.status='Réglages restaurés. Vérifier les chemins puis lancer l’indexation manuellement.'
            self.report({'INFO'},'Réglages importés, sans accès aux bibliothèques ni écriture dans les journaux')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


def register():
    for cls in (S3D_OT_export_settings,S3D_OT_import_settings):
        bpy.utils.register_class(cls)


def unregister():
    for cls in (S3D_OT_import_settings,S3D_OT_export_settings):
        bpy.utils.unregister_class(cls)
