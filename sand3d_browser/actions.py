"""Import, preview preparation and integration with Blender's Asset Browser."""
from pathlib import Path
import os
import subprocess
import uuid
import hashlib
import re
import json
import bpy
import bpy.utils.previews
from . import blender_ui as ui
from .catalog import local_root
from .model_io import import_model, checked_asset, dependencies, SUPPORTED
from .texture_recovery import MissingTextures
from .operation_log import event

PREVIEWS = None
READY = {}
JOB = None
PENDING = None


def recovery_needed(context, exc, operation):
    global PENDING
    item = selected(context)
    state = context.window_manager.sand3d_state
    previous = {issue.key: issue.replacement for issue in state.texture_issues} if PENDING and PENDING['key'] == key(item) else {}
    state.texture_issues.clear()
    for data in exc.issues:
        issue = state.texture_issues.add()
        issue.key, issue.expected, issue.reason = data['key'], data['expected'], data['reason']
        issue.replacement = previous.get(issue.key, '')
    PENDING = dict(key=key(item), operation=operation, uid=item.library_uid)
    state.status = str(exc) + ' : importer sans textures ou choisir les fichiers.'
    event(context, 'ERROR', 'missing_textures', exception=exc, source=item.relative_path,
          resources=exc.issues, operation=operation)
    if not bpy.app.background:
        bpy.ops.sand3d.texture_dialog('INVOKE_DEFAULT')


def recovery_controls(layout, context):
    state = context.window_manager.sand3d_state
    layout.label(text='Textures absentes ou à relocaliser')
    for index, issue in enumerate(state.texture_issues):
        box = layout.box()
        box.label(text=issue.expected)
        box.label(text=issue.replacement or 'Aucun fichier de remplacement choisi')
        box.operator('sand3d.choose_texture', text='Choisir le fichier…', icon='FILE_FOLDER').issue_index = index
    verb = 'Préparer' if PENDING and PENDING['operation'] == 'PREPARE' else 'Importer'
    layout.operator('sand3d.resume_textures', text=verb + ' le modèle sans aucune texture').omit = True
    layout.operator('sand3d.resume_textures', text='Continuer avec les fichiers choisis').omit = False
    layout.operator('sand3d.cancel_textures', text='Abandonner cette opération')


class S3D_OT_texture_dialog(bpy.types.Operator):
    bl_idname = 'sand3d.texture_dialog'
    bl_label = 'Ressources de texture manquantes'
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=650)
    def draw(self, context):
        if PENDING is None:
            self.layout.label(text=context.window_manager.sand3d_state.status)
        else:
            recovery_controls(self.layout, context)
    def execute(self, context):
        return {'FINISHED'}


class S3D_OT_choose_texture(bpy.types.Operator):
    bl_idname = 'sand3d.choose_texture'
    bl_label = 'Localiser la texture — choisir librement un fichier'
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    issue_index: bpy.props.IntProperty(options={'HIDDEN'})
    filter_glob: bpy.props.StringProperty(default='*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.exr;*.hdr;*.bmp;*.tga;*.webp', options={'HIDDEN'})
    def invoke(self, context, event):
        # No initial search or crawl; the user browses drives and directories.
        if not self.filepath:
            self.filepath = selected(context).root.rstrip('\\/') + os.sep
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    def execute(self, context):
        state = context.window_manager.sand3d_state
        if PENDING is None or not 0 <= self.issue_index < len(state.texture_issues):
            return {'CANCELLED'}
        path = Path(self.filepath)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            self.report({'ERROR'}, 'Le fichier choisi est inaccessible')
            return {'CANCELLED'}
        state.texture_issues[self.issue_index].replacement = str(path)
        event_log = dict(texture=state.texture_issues[self.issue_index].expected, replacement=str(path))
        event(context, 'INFO', 'texture_selected_by_user', **event_log)
        return {'FINISHED'}


class S3D_OT_resume_textures(bpy.types.Operator):
    bl_idname = 'sand3d.resume_textures'
    bl_label = 'Continuer l’opération'
    omit: bpy.props.BoolProperty(default=False)
    def execute(self, context):
        global PENDING
        try:
            item = selected(context)
            if PENDING is None or key(item) != PENDING['key'] or item.library_uid != PENDING['uid']:
                raise ValueError('La sélection a changé : relancez l’opération sur le modèle voulu')
            mapping = {issue.key: issue.replacement for issue in context.window_manager.sand3d_state.texture_issues if issue.replacement}
            operation = PENDING['operation']
            operator = bpy.ops.sand3d.import_selected if operation == 'IMPORT' else bpy.ops.sand3d.prepare_asset
            result = operator(omit=self.omit, replacements=json.dumps(mapping))
            # A new unresolved issue refreshes the list; clear only on success.
            if result == {'FINISHED'} and not context.window_manager.sand3d_state.status.startswith('Textures en attente'):
                PENDING = None
                context.window_manager.sand3d_state.texture_issues.clear()
            return result
        except Exception as exc:
            event(context, 'ERROR', 'texture_recovery_failed', exception=exc)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class S3D_OT_cancel_textures(bpy.types.Operator):
    bl_idname = 'sand3d.cancel_textures'
    bl_label = 'Abandonner la récupération'
    def execute(self, context):
        global PENDING
        PENDING = None
        context.window_manager.sand3d_state.texture_issues.clear()
        context.window_manager.sand3d_state.status = 'Opération abandonnée avant import.'
        event(context, 'INFO', 'texture_recovery_cancelled')
        return {'FINISHED'}


class S3D_OT_test_logs(bpy.types.Operator):
    bl_idname = 'sand3d.test_logs'
    bl_label = 'Vérifier les chemins des journaux'
    def execute(self, context):
        from .operation_log import validate_paths
        prefs = ui.preferences(context)
        try:
            if not prefs.general_log or not prefs.error_log:
                raise ValueError('Renseigner les deux fichiers de journal')
            validate_paths(prefs.general_log, prefs.error_log)
            # Create the error journal without writing a fake error record.
            with Path(prefs.error_log).open('a', encoding='utf-8'):
                pass
            if not event(context, 'INFO', 'journals_configured'):
                raise OSError('Écriture du journal impossible')
            prefs.logs_verified=True
            self.report({'INFO'}, 'Deux journaux configurés ; écriture en ajout, sans effacement')
            return {'FINISHED'}
        except (ValueError, OSError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


def selected(context):
    state = context.window_manager.sand3d_state
    if not 0 <= state.selected < len(state.results):
        raise ValueError('Sélectionnez un modèle')
    item = state.results[state.selected]
    if not hasattr(item, 'library_uid') or not hasattr(item, 'root'):
        raise ValueError('Ancienne version encore chargée : enregistrer le travail, redémarrer Blender puis réindexer')
    lib = next((l for l in ui.preferences(context).libraries if l.uid == item.library_uid), None)
    if lib is None or not lib.enabled or lib.directory != item.root:
        raise ValueError('Bibliothèque modifiée : relancez la recherche')
    return item


def key(item):
    return (getattr(item, 'root', ''), item.relative_path)


def selected_scale(context, item):
    return next(lib.unitless_scale for lib in ui.preferences(context).libraries if lib.uid == item.library_uid)


def icon(item):
    from . import thumbnails
    cached=thumbnails.preview(item)
    if cached:
        return cached.icon_id
    prepared = READY.get(key(item))
    if PREVIEWS is not None and prepared and prepared in PREVIEWS:
        return PREVIEWS[prepared].icon_id
    return 0


class S3D_OT_import(bpy.types.Operator):
    bl_idname = 'sand3d.import_selected'
    bl_label = 'Importer dans la scène'
    bl_description = 'Importer le modèle sélectionné dans une nouvelle collection'
    bl_options = {'REGISTER', 'UNDO'}
    replacements: bpy.props.StringProperty(default='{}', options={'HIDDEN'})
    omit: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

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
        if context.mode != 'OBJECT':
            self.report({'WARNING'}, 'Passez en mode Objet avant l’import')
            return {'CANCELLED'}
        try:
            item = selected(context)
            event(context, 'INFO', 'import_started', source=item.relative_path, library=item.root, omit_textures=self.omit)
            collection, objects = import_model(context, item.root, item.relative_path, selected_scale(context, item), json.loads(self.replacements), self.omit)
            context.window_manager.sand3d_state.status = f'{len(objects)} objet(s) importé(s) : {collection.name}'
            if collection.get('sand3d_muted_complex_drivers',0):
                self.report({'WARNING'},'Les pilotes Python complexes de la copie importée sont mis en pause')
            event(context, 'INFO', 'import_finished', source=item.relative_path, objects=len(objects), collection=collection.name)
            return {'FINISHED'}
        except MissingTextures as exc:
            recovery_needed(context, exc, 'IMPORT')
            context.window_manager.sand3d_state.status = 'Textures en attente : choisir les fichiers ou importer sans textures.'
            return {'FINISHED'}
        except Exception as exc:
            event(context, 'ERROR', 'import_failed', exception=exc)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


def refresh_job():
    global JOB
    if JOB is None:
        return None
    process, handle, output, item_key = JOB
    if process.poll() is None:
        return 0.5
    handle.close()
    JOB = None
    state = bpy.context.window_manager.sand3d_state
    if process.returncode == 0 and output.with_suffix('.blend').is_file():
        READY[item_key] = str(output)
        PREVIEWS.load(str(output), str(output.with_suffix('.png')), 'IMAGE')
        state.status = 'Miniature prête. Ouvrez l’Asset Browser pour glisser-déposer.'
        event(bpy.context, 'INFO', 'preparation_finished', output=str(output), source=item_key)
    else:
        state.status = 'Préparation échouée : consulter ' + str(output.with_suffix('.log'))
        try:
            with output.with_suffix('.log').open('rb') as stream:
                stream.seek(max(0, output.with_suffix('.log').stat().st_size - 32768))
                details = stream.read().decode('utf-8', errors='replace')
        except OSError:
            details = 'Journal du worker inaccessible'
        event(bpy.context, 'ERROR', 'preparation_failed', output=str(output), returncode=process.returncode, worker_report=details)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    return None


class S3D_OT_prepare(bpy.types.Operator):
    bl_idname = 'sand3d.prepare_asset'
    bl_label = 'Créer miniature et asset glissable'
    bl_description = 'Créer un aperçu et une copie Blender dans le dossier préparé, sans modifier la source'
    replacements: bpy.props.StringProperty(default='{}', options={'HIDDEN'})
    omit: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def execute(self, context):
        global JOB
        if JOB is not None:
            self.report({'WARNING'}, 'Une préparation est déjà en cours')
            return {'CANCELLED'}
        try:
            item = selected(context)
            prefs = ui.preferences(context)
            if not prefs.prepared_directory:
                raise ValueError('Définir le Dossier des assets préparés dans Configurer les bibliothèques avant de créer la miniature')
            output_root = local_root(prefs.prepared_directory)
            mapping = json.loads(self.replacements)
            source_path, resources = dependencies(item.root, item.relative_path, mapping, self.omit)
            # A nested output is allowed: the index excludes its whole subtree.
            for lib in prefs.libraries:
                if lib.directory:
                    source = Path(os.path.abspath(lib.directory))
                    if source.is_relative_to(output_root):
                        raise ValueError('Le dossier de préparation ne doit pas être la bibliothèque ni son parent')
            if source_path.is_relative_to(output_root):
                raise ValueError('Ne pas préparer de nouveau un fichier déjà situé dans le dossier de sortie')
            libraries = context.preferences.filepaths.asset_libraries
            if not any(Path(l.path) == output_root for l in libraries):
                libraries.new(name='MZERMARTS Sand3D', directory=str(output_root))
            scale = selected_scale(context, item)
            records = [(str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(resources)]
            fingerprint = hashlib.sha256(repr(('0.5.1', records, scale, self.omit, sorted(mapping.items()))).encode()).hexdigest()[:16]
            stem = re.sub(r'[^\w-]+', '_', source_path.stem)[:60]
            output = output_root / (stem + '_' + fingerprint)
            if output.with_suffix('.blend').is_file() and output.with_suffix('.png').is_file():
                READY[key(item)] = str(output)
                if str(output) not in PREVIEWS:
                    PREVIEWS.load(str(output), str(output.with_suffix('.png')), 'IMAGE')
                context.window_manager.sand3d_state.status = 'Asset préparé retrouvé dans le cache.'
                event(context, 'INFO', 'preparation_cache_hit', source=item.relative_path, output=str(output))
                return {'FINISHED'}
            if any(output.with_suffix(suffix).exists() for suffix in ('.log', '.png', '.blend')):
                output = output_root / (output.name + '_retry_' + uuid.uuid4().hex[:8])
            profile = output_root / ('profil_' + uuid.uuid4().hex[:12])
            env = os.environ.copy()
            for variable, suffix in {
                'BLENDER_USER_RESOURCES': '', 'BLENDER_USER_CONFIG': 'config',
                'BLENDER_USER_SCRIPTS': 'scripts', 'BLENDER_USER_EXTENSIONS': 'extensions',
                'BLENDER_USER_DATAFILES': 'datafiles',
            }.items():
                folder = profile / suffix
                folder.mkdir(parents=True, exist_ok=True)
                env[variable] = str(folder)
            args = [bpy.app.binary_path, '--background', '--factory-startup', '--disable-autoexec',
                    '--python-exit-code', '1', '--python', str(Path(__file__).with_name('prepare_asset.py')),
                    '--', item.root, item.relative_path, str(output), str(scale), json.dumps(dict(replacements=mapping, omit=self.omit))]
            log = output.with_suffix('.log').open('x', encoding='utf-8')
            try:
                process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env,
                                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except Exception:
                log.close()
                raise
            JOB = process, log, output, key(item)
            event(context, 'INFO', 'preparation_started', source=item.relative_path, output=str(output), omit_textures=self.omit)
            context.window_manager.sand3d_state.status = 'Préparation en arrière-plan…'
            bpy.app.timers.register(refresh_job, first_interval=0.5)
            return {'FINISHED'}
        except MissingTextures as exc:
            recovery_needed(context, exc, 'PREPARE')
            context.window_manager.sand3d_state.status = 'Textures en attente : choisir les fichiers ou préparer sans textures.'
            return {'FINISHED'}
        except Exception as exc:
            event(context, 'ERROR', 'preparation_failed', exception=exc)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class S3D_OT_copy_path(bpy.types.Operator):
    bl_idname = 'sand3d.copy_path'
    bl_label = 'Copier le chemin du modèle'

    def execute(self, context):
        try:
            item = selected(context)
            context.window_manager.clipboard = str(Path(item.root) / item.relative_path)
            event(context, 'INFO', 'source_path_copied', source=item.relative_path)
            return {'FINISHED'}
        except ValueError as exc:
            self.report({'WARNING'}, str(exc))
            return {'CANCELLED'}


class S3D_OT_asset_browser(bpy.types.Operator):
    bl_idname = 'sand3d.open_asset_browser'
    bl_label = 'Ouvrir l’Asset Browser'
    bl_description = 'Ouvrir une fenêtre Blender dédiée aux assets préparés'

    def execute(self, context):
        if context.window is None:
            return {'CANCELLED'}
        before = set(context.window_manager.windows)
        bpy.ops.wm.window_new()
        window = next((w for w in context.window_manager.windows if w not in before), None)
        if window is None:
            return {'CANCELLED'}
        area = max(window.screen.areas, key=lambda a: a.width * a.height)
        area.type = 'FILE_BROWSER'
        area.ui_type = 'ASSETS'
        # ALL is robust even when another library has the same display name.
        if area.spaces.active.params is not None:
            area.spaces.active.params.asset_library_reference = 'ALL'
        event(context, 'INFO', 'asset_browser_opened')
        return {'FINISHED'}


def draw_actions(layout, context):
    supported = False
    try:
        supported = selected(context).format in SUPPORTED
    except ValueError:
        pass
    row = layout.column()
    row.enabled = supported
    row.operator('sand3d.import_selected', icon='IMPORT')
    row.operator('sand3d.prepare_asset', icon='RENDER_STILL')
    layout.operator('sand3d.open_asset_browser', icon='ASSET_MANAGER')
    layout.operator('sand3d.copy_path', icon='COPYDOWN')


def list_context_menu(self, context):
    listing = getattr(context, 'ui_list', None)
    if listing and listing.bl_idname == 'S3D_UL_results':
        self.layout.separator()
        draw_actions(self.layout, context)


CLASSES = (S3D_OT_texture_dialog, S3D_OT_choose_texture, S3D_OT_resume_textures, S3D_OT_cancel_textures,
           S3D_OT_test_logs, S3D_OT_import, S3D_OT_prepare, S3D_OT_copy_path, S3D_OT_asset_browser)


def register():
    global PREVIEWS
    PREVIEWS = bpy.utils.previews.new()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.UI_MT_list_item_context_menu.append(list_context_menu)


def unregister():
    global PREVIEWS, JOB, PENDING
    # Stop the isolated worker without touching source files or deleting output.
    if JOB is not None:
        process, handle, output, item_key = JOB
        process.terminate()
        process.wait(timeout=10)
        handle.close()
        JOB = None
    if bpy.app.timers.is_registered(refresh_job):
        bpy.app.timers.unregister(refresh_job)
    bpy.types.UI_MT_list_item_context_menu.remove(list_context_menu)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    bpy.utils.previews.remove(PREVIEWS)
    PREVIEWS = None
    READY.clear()
    PENDING = None
