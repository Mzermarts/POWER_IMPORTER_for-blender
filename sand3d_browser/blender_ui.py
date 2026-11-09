"""Blender preferences and session-local index. No persistent cache yet."""
import time
import uuid
import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, StringProperty, FloatProperty, EnumProperty
from .catalog import local_root, scan, search, IMAGE_FORMATS
from .operation_log import event
from .operation_log import event as event_log

PACKAGE = __package__
INDEX = {}
RUNNING = False
ACTIVE_JOB = None


def search_changed(self,context):
    if context and not RUNNING and PACKAGE in context.preferences.addons:
        if self.page != 1:
            self.page = 1
        else:
            bpy.ops.sand3d.search(reset_page=False)


def page_changed(self,context):
    if context and not RUNNING and PACKAGE in context.preferences.addons:
        bpy.ops.sand3d.search(reset_page=False)


def output_changed(self,context):
    INDEX.clear()
    if context and hasattr(context.window_manager,'sand3d_state'):
        state=context.window_manager.sand3d_state
        state.results.clear()
        state.status='Dossier de préparation modifié : réindexer les bibliothèques.'


def size_label(size):
    size=float(size)
    for unit in ('o','Ko','Mo','Go','To'):
        if size<1024 or unit=='To':
            return f'{size:.0f} {unit}' if unit=='o' else f'{size:.1f} {unit}'
        size/=1024


def selection_changed(self,context):
    if 0<=self.selected<len(self.results):
        from . import thumbnails
        thumbnails.request(self.results[self.selected])


def log_paths_changed(self,context):
    self.logs_verified=False


def invalidate(self, context):
    INDEX.pop(self.uid, None)
    if context and hasattr(context.window_manager, "sand3d_state"):
        context.window_manager.sand3d_state.results.clear()


def preferences(context):
    return context.preferences.addons[PACKAGE].preferences


class S3DLibrary(bpy.types.PropertyGroup):
    uid: StringProperty()
    name: StringProperty(name="Nom", default="Bibliothèque locale")
    directory: StringProperty(name="Dossier", subtype='DIR_PATH', update=invalidate)
    enabled: BoolProperty(name="Active", default=True, update=invalidate)
    recursive: BoolProperty(name="Inclure les sous-dossiers", default=True, update=invalidate)
    unitless_scale: FloatProperty(name="Échelle OBJ / STL", default=1.0, min=0.000001,
        description="Multiplicateur des coordonnées OBJ/STL, formats sans unité fiable ; 1 conserve les valeurs")


class S3DResult(bpy.types.PropertyGroup):
    size_text: StringProperty()
    relative_path: StringProperty()
    library_name: StringProperty()
    format: StringProperty()
    root: StringProperty()
    library_uid: StringProperty()


class S3DTextureIssue(bpy.types.PropertyGroup):
    key: StringProperty()
    expected: StringProperty()
    reason: StringProperty()
    replacement: StringProperty(subtype='FILE_PATH')


class S3DState(bpy.types.PropertyGroup):
    destination_scene: bpy.props.PointerProperty(type=bpy.types.Scene,options={'SKIP_SAVE'})
    destination_layer: StringProperty(options={'SKIP_SAVE'})
    page: IntProperty(name='Page',default=1,min=1,update=page_changed)
    page_size: IntProperty(name='Résultats par page',default=1000,min=50,max=10000,update=search_changed)
    total: IntProperty(default=0)
    page_count: IntProperty(default=1)
    view_mode: EnumProperty(name='Affichage',items=[('LIST','Liste détaillée',''),('SMALL','Petites vignettes',''),('LARGE','Grandes vignettes','')],default='SMALL')
    query: StringProperty(name="Recherche", description="Mots ou jokers : *.obj, *.blend, room*, *rock*",update=search_changed)
    results: CollectionProperty(type=S3DResult)
    selected: IntProperty(default=0,update=selection_changed)
    status: StringProperty(default="Ajoutez un dossier dans les préférences, puis indexez-le.")
    cancel: BoolProperty(default=False)
    texture_issues: CollectionProperty(type=S3DTextureIssue)
    format_filter: EnumProperty(name="Formats", items=[
        ('ALL', 'Tous', ''), ('USD', 'USD / USDA / USDC', ''), ('OBJ', 'OBJ', ''),
        ('STL', 'STL', ''), ('GLTF', 'GLB / glTF', ''), ('BLEND','Blender .blend',''),
        ('IMAGES','Images',''),('3MF', '3MF (inventaire)', '')], default='ALL',update=search_changed)
    image_role: EnumProperty(name='Rôle de l’image',items=[('COLOR','Couleur',''),('ROUGHNESS','Rugosité',''),('NORMAL','Normale',''),('ALPHA','Transparence','')],default='COLOR')
    image_uv: StringProperty(name='Carte UV')


class S3D_UL_libraries(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "name", text="", emboss=False)


class S3DPreferences(bpy.types.AddonPreferences):
    bl_idname = PACKAGE
    libraries: CollectionProperty(type=S3DLibrary)
    active_library: IntProperty(default=0)
    prepared_directory: StringProperty(name="Dossier des copies Blender et miniatures", subtype='DIR_PATH',
        description="Dossier existant réservé aux copies ; automatiquement exclu de l’index",update=output_changed)
    logs_verified: BoolProperty(default=False,options={'SKIP_SAVE'})
    general_log: StringProperty(name="Journal général", subtype='FILE_PATH',update=log_paths_changed,
        description="Chemin absolu .log/.jsonl/.txt ; opérations, avertissements et erreurs en ajout. Vide : désactivé")
    error_log: StringProperty(name="Journal des erreurs uniquement", subtype='FILE_PATH',update=log_paths_changed,
        description="Second fichier distinct, erreurs et traces techniques en ajout. Vide : désactivé")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Bibliothèques locales ou réseau — lecture seule")
        controls = layout.column()
        controls.enabled = not RUNNING
        row = controls.row()
        row.template_list("S3D_UL_libraries", "", self, "libraries", self, "active_library", rows=4)
        buttons = row.column(align=True)
        buttons.operator("sand3d.library_add", text="", icon='ADD')
        buttons.operator("sand3d.library_remove", text="", icon='REMOVE')
        if 0 <= self.active_library < len(self.libraries):
            lib = self.libraries[self.active_library]
            controls.prop(lib, "directory")
            controls.prop(lib, "recursive")
            controls.prop(lib, "unitless_scale")
        layout.label(text="N’ajouter que des dossiers professionnels autorisés.")
        layout.label(text="Lecteurs mappés et chemins UNC acceptés ; liens exclus.")
        layout.label(text="Choisir les dossiers autorisés, pas la racine du serveur.")
        controls.operator("sand3d.index", icon='FILE_REFRESH')
        layout.label(text="Enregistrez les préférences selon votre réglage Blender.")
        output=layout.column()
        output.enabled=not RUNNING
        output.prop(self, "prepared_directory")
        layout.label(text='Ce dossier et ses sous-dossiers sont exclus de l’indexation.')
        layout.label(text="Préparation : copies .blend + PNG ; sources conservées.")
        box = layout.box()
        box.label(text="Journaux locaux — deux fichiers distincts, sans effacement")
        box.prop(self, "general_log")
        box.prop(self, "error_log")
        box.operator('sand3d.test_logs')
        from .operation_log import LAST_ERROR
        label='Désactivés' if not self.general_log and not self.error_log else 'Configurés, non vérifiés'
        if self.logs_verified:
            label='Écriture vérifiée'
        if LAST_ERROR:
            label='Erreur d’écriture : '+LAST_ERROR
        box.label(text='État des journaux : '+label)
        row=layout.row(align=True)
        row.operator('sand3d.export_settings',icon='EXPORT')
        row.operator('sand3d.import_settings',icon='IMPORT')
        layout.label(text='Réglages uniquement : aucun fichier de bibliothèque déplacé.')


class S3D_OT_add(bpy.types.Operator):
    bl_idname = "sand3d.library_add"
    bl_label = "Ajouter une bibliothèque"

    def execute(self, context):
        if RUNNING:
            return {'CANCELLED'}
        prefs = preferences(context)
        lib = prefs.libraries.add()
        lib.uid = uuid.uuid4().hex
        prefs.active_library = len(prefs.libraries) - 1
        event(context, 'INFO', 'library_added', uid=lib.uid)
        return {'FINISHED'}


class S3D_OT_remove(bpy.types.Operator):
    bl_idname = "sand3d.library_remove"
    bl_label = "Retirer le chemin de la liste"
    bl_description = "Retirer la configuration sans supprimer les fichiers du dossier"

    def execute(self, context):
        if RUNNING:
            return {'CANCELLED'}
        prefs = preferences(context)
        if not 0 <= prefs.active_library < len(prefs.libraries):
            return {'CANCELLED'}
        event(context, 'INFO', 'library_removed', directory=prefs.libraries[prefs.active_library].directory)
        INDEX.pop(prefs.libraries[prefs.active_library].uid, None)
        prefs.libraries.remove(prefs.active_library)
        prefs.active_library = max(0, min(prefs.active_library, len(prefs.libraries) - 1))
        context.window_manager.sand3d_state.results.clear()
        return {'FINISHED'}


class S3D_OT_search(bpy.types.Operator):
    bl_idname = "sand3d.search"
    bl_label = "Rechercher"
    reset_page: BoolProperty(default=True,options={'HIDDEN'})

    def execute(self, context):
        state = context.window_manager.sand3d_state
        if self.reset_page and state.page!=1:
            state.page=1
            return {'FINISHED'}
        state.results.clear()
        state.selected=-1
        total = 0
        for lib in preferences(context).libraries:
            cached = INDEX.get(lib.uid)
            if not lib.enabled or not cached:
                continue
            if cached[:2] != (lib.directory, lib.recursive):
                continue
            for asset in search(cached[2], state.query):
                group = 'IMAGES' if '.'+asset.format in IMAGE_FORMATS else 'USD' if asset.format in {'usd', 'usda', 'usdc'} else 'GLTF' if asset.format in {'glb', 'gltf'} else asset.format.upper()
                if state.format_filter != 'ALL' and state.format_filter != group:
                    continue
                total += 1
                if (state.page-1)*state.page_size <= total-1 < state.page*state.page_size:
                    item = state.results.add()
                    item.relative_path = asset.relative_path
                    item.library_name = lib.name
                    item.format = asset.format
                    item.root = lib.directory
                    item.library_uid = lib.uid
                    item.size_text = size_label(asset.size)
        state.total=total
        state.page_count=max(1,(total+state.page_size-1)//state.page_size)
        if state.page>state.page_count:
            state.page=state.page_count
            return {'FINISHED'}
        state.selected = 0
        state.status = f"{total} résultat(s) · page {state.page}/{state.page_count} · {len(state.results)} affichés."
        event(context, 'INFO', 'search_finished', query=state.query, format=state.format_filter, results=total)
        return {'FINISHED'}


class S3D_OT_index(bpy.types.Operator):
    bl_idname = "sand3d.index"
    bl_label = "Indexer les bibliothèques actives"
    bl_description = "Lire uniquement les noms et tailles des modèles ; Échap pour arrêter"
    _timer = None
    _iterator = None

    def _work(self, context):
        prefs = preferences(context)
        seen = set()
        count = warnings = 0
        state = context.window_manager.sand3d_state
        for lib in prefs.libraries:
            if not lib.enabled:
                continue
            try:
                key = str(local_root(lib.directory)).casefold()
                if key in seen:
                    warnings += 1
                    continue
                seen.add(key)
                items = []
                for asset, warning in scan(lib.directory, lib.recursive, excluded=(prefs.prepared_directory,)):
                    if asset:
                        items.append(asset)
                        count += 1
                    warnings += bool(warning)
                    if warning:
                        level = 'ERROR' if 'inaccessible' in warning.lower() else 'WARNING'
                        event(context, level, 'index_resource_report', directory=lib.directory, message=warning)
                    state.status = f"Indexation : {lib.name} — {count} modèle(s), {warnings} avertissement(s)"
                    yield
                INDEX[lib.uid] = (lib.directory, lib.recursive, items)
                event(context, 'INFO', 'library_indexed', directory=lib.directory, models=len(items), warnings=warnings)
            except (OSError, ValueError) as exc:
                INDEX.pop(lib.uid, None)
                warnings += 1
                self.report({'WARNING'}, f"{lib.name} : {exc}")
                event(context, 'ERROR', 'library_index_failed', exception=exc, directory=lib.directory)
                yield
        bpy.ops.sand3d.search()
        state.status += f" Avertissements : {warnings}."
        event(context, 'INFO', 'index_finished', models=count, warnings=warnings)

    def execute(self, context):
        global RUNNING, ACTIVE_JOB
        if RUNNING:
            return {'CANCELLED'}
        RUNNING = True
        event(context, 'INFO', 'index_started', libraries=[l.directory for l in preferences(context).libraries if l.enabled])
        ACTIVE_JOB = self
        context.window_manager.sand3d_state.cancel = False
        context.window_manager.sand3d_state.page = 1
        context.window_manager.sand3d_state.results.clear()
        # Rebuild only on explicit request; no stale snapshot after an interrupted scan.
        INDEX.clear()
        self._iterator = self._work(context)
        if bpy.app.background:
            try:
                for _ in self._iterator:
                    pass
            finally:
                self.finish(context)
            return {'FINISHED'}
        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def finish(self, context):
        global RUNNING, ACTIVE_JOB
        if self._iterator is not None:
            self._iterator.close()
            self._iterator = None
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        RUNNING = False
        ACTIVE_JOB = None

    def modal(self, context, event):
        if event.type == 'ESC' or context.window_manager.sand3d_state.cancel:
            self.finish(context)
            context.window_manager.sand3d_state.status = "Indexation arrêtée ; seules les bibliothèques terminées sont disponibles."
            event_log(context, 'INFO', 'index_cancelled')
            return {'CANCELLED'}
        if event.type == 'TIMER':
            deadline = time.monotonic() + 0.02
            try:
                while time.monotonic() < deadline:
                    next(self._iterator)
            except StopIteration:
                self.finish(context)
                return {'FINISHED'}
            except Exception as exc:
                self.finish(context)
                event_log(context, 'ERROR', 'index_failed', exception=exc)
                self.report({'ERROR'}, str(exc))
                return {'CANCELLED'}
            for area in context.screen.areas:
                area.tag_redraw()
        return {'PASS_THROUGH'}

    def cancel(self, context):
        self.finish(context)


class S3D_OT_stop(bpy.types.Operator):
    bl_idname = "sand3d.stop"
    bl_label = "Arrêter l’indexation"

    def execute(self, context):
        context.window_manager.sand3d_state.cancel = True
        return {'FINISHED'}


class S3D_UL_results(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from .actions import icon as preview_icon
        from . import thumbnails
        thumbnails.request(item)
        preview = preview_icon(item)
        if preview:
            layout.label(text=item.relative_path, icon_value=preview)
        else:
            layout.label(text=item.relative_path, icon='MESH_DATA')
        layout.label(text=item.library_name)
        layout.label(text=item.format.upper()+' · '+item.size_text)


class S3D_OT_page(bpy.types.Operator):
    bl_idname='sand3d.result_page'
    bl_label='Changer de page'
    delta: IntProperty(default=1)
    def execute(self,context):
        state=context.window_manager.sand3d_state
        state.page=max(1,min(state.page_count,state.page+self.delta))
        return {'FINISHED'}


class S3D_PT_browser(bpy.types.Panel):
    bl_label = "Power Importer — Bibliothèques 0.7.0"
    bl_idname = "S3D_PT_browser"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Power Importer"

    def draw(self, context):
        layout = self.layout
        state = context.window_manager.sand3d_state
        row=layout.row(align=True)
        row.operator('sand3d.open_browser',text='Onglet',icon='WORKSPACE').mode='WORKSPACE'
        row.operator('sand3d.open_browser',text='Fenêtre',icon='WINDOW').mode='WINDOW'
        from .browser_windows import is_browser
        box=layout.box()
        target=state.destination_scene
        box.label(text='Destination : '+(target.name if target else 'scène courante'))
        if not is_browser(context):
            box.operator('sand3d.set_destination',icon='SCENE_DATA')
        elif target is None:
            box.label(text='Définir la destination depuis le Layout.',icon='ERROR')
        else:
            box.label(text='View Layer : '+state.destination_layer)
        op = layout.operator("preferences.addon_show", text="Configurer les bibliothèques", icon='PREFERENCES')
        op.module = PACKAGE
        if RUNNING:
            layout.operator("sand3d.stop", icon='CANCEL')
        else:
            layout.operator("sand3d.index", icon='FILE_REFRESH')
        col = layout.column()
        col.enabled = not RUNNING
        col.prop(state, "query", text="", icon='VIEWZOOM')
        col.prop(state, "format_filter", text="")
        col.operator("sand3d.search")
        modes=col.row(align=True)
        for mode,label,icon in (('LIST','Liste','LINENUMBERS_ON'),('SMALL','Petites','IMAGE_DATA'),('LARGE','Grandes','IMAGE_DATA')):
            op=modes.operator('sand3d.gallery',text=label,icon=icon,depress=state.view_mode==mode)
            op.mode=mode
        nav=col.row(align=True)
        nav.operator('sand3d.result_page',text='',icon='TRIA_LEFT').delta=-1
        nav.prop(state,'page',text='Page')
        nav.label(text='/ '+str(state.page_count))
        nav.operator('sand3d.result_page',text='',icon='TRIA_RIGHT').delta=1
        col.prop(state,'page_size')
        col.template_list("S3D_UL_results", "", state, "results", state, "selected", rows=7)
        if 0 <= state.selected < len(state.results):
            item = state.results[state.selected]
            col.label(text=f"Format : {item.format.upper()}")
            col.label(text='Taille : '+item.size_text)
            from .actions import icon as preview_icon, draw_actions
            preview = preview_icon(item)
            if preview:
                col.template_icon(icon_value=preview, scale=8)
            if item.format == '3mf':
                col.label(text="3MF : extension distincte nécessaire ; inventaire uniquement.")
            elif item.format in {'obj', 'stl'}:
                col.label(text="OBJ/STL : vérifier l’échelle dans les préférences.")
            if '.'+item.format in IMAGE_FORMATS:
                from .image_actions import draw
                draw(col,context)
            else:
                draw_actions(col, context)
        from .actions import PENDING, recovery_controls
        if PENDING is not None and len(state.texture_issues):
            recovery_controls(layout.box(), context)
        layout.label(text=state.status)
        from .operation_log import LAST_ERROR
        if LAST_ERROR:
            layout.label(text='Journal inaccessible : ' + LAST_ERROR, icon='ERROR')
        layout.label(text="Modèles : glisser-déposer via l’Asset Browser après préparation.")


CLASSES = (S3DLibrary, S3DResult, S3DTextureIssue, S3DState, S3D_UL_libraries, S3DPreferences,
           S3D_OT_add, S3D_OT_remove, S3D_OT_search, S3D_OT_page, S3D_OT_index, S3D_OT_stop,
           S3D_UL_results, S3D_PT_browser)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.sand3d_state = bpy.props.PointerProperty(type=S3DState)


def unregister():
    if ACTIVE_JOB is not None:
        ACTIVE_JOB.finish(bpy.context)
    del bpy.types.WindowManager.sand3d_state
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    INDEX.clear()
