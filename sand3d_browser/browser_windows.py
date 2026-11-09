"""Native workspace/window hosting with an explicit, validated import destination."""
from contextlib import contextmanager
import bpy

MARKER = 'mzermarts_power_importer_workspace'
TARGET_WINDOW = None
TARGET_WORKSPACE = None
BROWSER_WINDOWS = set()


def is_browser(context):
    return bool(context.workspace and context.workspace.get(MARKER)) or (
        context.window is not None and context.window.as_pointer() in BROWSER_WINDOWS)


def capture(context):
    global TARGET_WINDOW, TARGET_WORKSPACE
    if context.window is None or is_browser(context):
        raise ValueError('Choisir la scène dans le Layout, puis définir la destination depuis son panneau Power Importer')
    TARGET_WINDOW = context.window
    TARGET_WORKSPACE = context.workspace
    state = context.window_manager.sand3d_state
    state.destination_scene = context.scene
    state.destination_layer = context.view_layer.name


@contextmanager
def destination(context):
    if not is_browser(context):
        yield context
        return
    state = context.window_manager.sand3d_state
    try:
        window = TARGET_WINDOW
        if window is None or not any(w==window for w in context.window_manager.windows):
            raise ValueError('Fenêtre de destination fermée : redéfinir la destination depuis le Layout')
        scene = state.destination_scene
        if scene is None or window.scene != scene:
            raise ValueError('La scène de destination a changé : redéfinir la destination depuis le Layout')
        layer = scene.view_layers.get(state.destination_layer)
        if layer is None or window.view_layer != layer:
            raise ValueError('Le View Layer de destination a changé : redéfinir la destination depuis le Layout')
        area = next((a for a in window.screen.areas if a.type == 'VIEW_3D'), None)
        if area is None:
            raise ValueError('La fenêtre de destination doit contenir une vue 3D')
        region = next(r for r in area.regions if r.type == 'WINDOW')
    except ReferenceError:
        raise ValueError('Destination devenue indisponible : la redéfinir depuis le Layout') from None
    with context.temp_override(window=window, area=area, region=region):
        yield bpy.context


def configure(area):
    area.type = 'VIEW_3D'
    space = area.spaces.active
    space.show_region_ui = True
    space.show_region_toolbar = False
    space.overlay.show_overlays = False
    # The tab is selected after layout calculation, when the region exists.


def show_gallery(window, area):
    def start():
        try:
            if not any(w==window for w in bpy.context.window_manager.windows) or not any(a==area for a in window.screen.areas):
                return None
            region = next(r for r in area.regions if r.type == 'WINDOW')
            with bpy.context.temp_override(window=window, area=area, region=region):
                sidebar = next((r for r in area.regions if r.type == 'UI'), None)
                if sidebar is not None and hasattr(sidebar, 'active_panel_category'):
                    sidebar.active_panel_category = 'Power Importer'
                bpy.ops.sand3d.gallery('INVOKE_DEFAULT')
        except (ReferenceError, RuntimeError) as exc:
            print('Power Importer: ouvrir la galerie depuis le panneau :', exc)
        return None
    bpy.app.timers.register(start, first_interval=0.2)


class S3D_OT_destination(bpy.types.Operator):
    bl_idname = 'sand3d.set_destination'
    bl_label = 'Utiliser cette scène comme destination'
    bl_description = 'Mémoriser la fenêtre, la scène et le View Layer de travail courants'

    def execute(self, context):
        try:
            capture(context)
            self.report({'INFO'}, 'Destination : ' + context.scene.name)
            return {'FINISHED'}
        except ValueError as exc:
            self.report({'WARNING'}, str(exc))
            return {'CANCELLED'}


class S3D_OT_browser(bpy.types.Operator):
    bl_idname = 'sand3d.open_browser'
    bl_label = 'Ouvrir Power Importer'
    mode: bpy.props.EnumProperty(items=[('WORKSPACE', 'Onglet', ''), ('WINDOW', 'Fenêtre indépendante', '')])

    def execute(self, context):
        try:
            if context.window is None or bpy.app.background:
                raise ValueError('Une fenêtre Blender est nécessaire')
            if not is_browser(context):
                capture(context)
            elif TARGET_WINDOW is None:
                raise ValueError('Définir d’abord une destination depuis le Layout')
            from . import gallery
            if gallery.ACTIVE is not None:
                gallery.ACTIVE.finish(context)
            if self.mode == 'WINDOW':
                before = set(context.window_manager.windows)
                # A secondary child window shares its parent's scene selection.
                # A main window provides the independent scene context we need.
                bpy.ops.wm.window_new_main()
                window = next((w for w in context.window_manager.windows if w not in before), None)
                if window is None:
                    raise ValueError('La fenêtre indépendante n’a pas pu être créée')
                BROWSER_WINDOWS.add(window.as_pointer())
                area = max(window.screen.areas, key=lambda a: a.width * a.height)
                with context.temp_override(window=window,area=area):
                    bpy.ops.screen.screen_full_area(use_hide_panels=False)
                area = max(window.screen.areas, key=lambda a: a.width * a.height)
            else:
                workspace = next((w for w in bpy.data.workspaces if w.get(MARKER)), None)
                if workspace is None:
                    before = set(bpy.data.workspaces)
                    bpy.ops.workspace.duplicate()
                    workspace = next((w for w in bpy.data.workspaces if w not in before), None)
                    if workspace is None:
                        raise ValueError('L’espace de travail n’a pas pu être créé')
                    workspace.name = 'Power Importer'
                    workspace[MARKER] = True
                context.window.workspace = workspace
                window = context.window
                area = max(window.screen.areas, key=lambda a: a.width * a.height)
            configure(area)
            show_gallery(window, area)
            return {'FINISHED'}
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


def register():
    for cls in (S3D_OT_destination, S3D_OT_browser):
        bpy.utils.register_class(cls)


def unregister():
    global TARGET_WINDOW, TARGET_WORKSPACE
    TARGET_WINDOW = TARGET_WORKSPACE = None
    BROWSER_WINDOWS.clear()
    for cls in (S3D_OT_browser, S3D_OT_destination):
        bpy.utils.unregister_class(cls)
