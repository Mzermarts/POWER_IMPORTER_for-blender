"""Bounded, lazy image previews; viewing never imports a model into the scene."""
from collections import OrderedDict
import bpy
import bpy.utils.previews
from .catalog import IMAGE_FORMATS,local_root

CACHE=None
QUEUE=OrderedDict()
FAILED=set()


def cache_key(item):
    return item.root+'|'+item.relative_path


def request(item):
    key=cache_key(item)
    if CACHE is None or key in CACHE or key in FAILED:
        return
    from .actions import READY,key as action_key
    if '.'+item.format in IMAGE_FORMATS or action_key(item) in READY:
        QUEUE[key]=(item.root,item.relative_path,item.format,READY.get(action_key(item)))
        if not bpy.app.timers.is_registered(tick):
            bpy.app.timers.register(tick,first_interval=0.05)


def preview(item):
    if CACHE is not None:
        return CACHE.get(cache_key(item))


def tick():
    if not QUEUE or CACHE is None:
        return None
    key,(root,relative,extension,prepared)=QUEUE.popitem(last=False)
    try:
        from .model_io import scoped_path
        if prepared:
            path=prepared+'.png'
        else:
            path=scoped_path(local_root(root),local_root(root),relative)
        if len(CACHE)>=96:
            del CACHE[next(iter(CACHE))]
        CACHE.load(key,str(path),'IMAGE')
    except (ValueError,OSError,RuntimeError):
        FAILED.add(key)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                area.tag_redraw()
    return 0.05 if QUEUE else None


def register():
    global CACHE
    CACHE=bpy.utils.previews.new()


def unregister():
    global CACHE
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    QUEUE.clear()
    FAILED.clear()
    bpy.utils.previews.remove(CACHE)
    CACHE=None
