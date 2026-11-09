"""Local library browser; no network access or execution of asset code."""

bl_info = {
    "name": "MZERMARTS Power Importer",
    "author": "MZERMARTS",
    "version": (0, 7, 0),
    "blender": (5, 0, 0),
    "location": "Preferences > Add-ons; View3D > Sidebar > Power Importer",
    "description": "Configure local libraries and search their model files",
    "category": "3D View",
}


def register():
    # Blender may reload only __init__ on an install/update. Refresh submodules
    # in dependency order after the previous version has been disabled.
    import importlib
    import sys
    for name in ('catalog', 'operation_log', 'settings_io', 'texture_recovery', 'usd_io','blend_io', 'model_io', 'blender_ui', 'actions','thumbnails','gallery','image_actions','settings_ops','browser_windows'):
        qualified = __name__ + '.' + name
        if qualified in sys.modules:
            importlib.reload(sys.modules[qualified])
        else:
            importlib.import_module(qualified)
    from . import blender_ui, actions,thumbnails,gallery,image_actions,settings_ops,browser_windows
    blender_ui.register()
    actions.register()
    thumbnails.register()
    gallery.register()
    image_actions.register()
    settings_ops.register()
    browser_windows.register()


def unregister():
    from . import blender_ui, actions,thumbnails,gallery,image_actions,settings_ops,browser_windows
    browser_windows.unregister()
    settings_ops.unregister()
    image_actions.unregister()
    gallery.unregister()
    thumbnails.unregister()
    actions.unregister()
    blender_ui.unregister()
