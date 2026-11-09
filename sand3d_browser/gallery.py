"""Viewport gallery with deterministic hit boxes and enlarged hover preview."""
import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_texture_2d
from . import thumbnails

ACTIVE=None


def visible_width(region, area=None):
    width=region.width
    if area is not None:
        space=area.spaces.active
        for other in area.regions:
            if other.type=='UI' and getattr(space,'show_region_ui',False) and other.width>1:
                if other.x>region.x:
                    width=min(width,other.x-region.x)
    return max(1,width)


def rect(x,y,w,h,color):
    shader=gpu.shader.from_builtin('UNIFORM_COLOR')
    batch=batch_for_shader(shader,'TRI_FAN',{'pos':[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]})
    shader.bind()
    shader.uniform_float('color',color)
    batch.draw(shader)


def text(x,y,value,size=12):
    blf.size(0,size)
    blf.position(0,x,y,0)
    blf.color(0,0.95,0.95,0.95,1)
    blf.draw(0,value)


class S3D_OT_gallery(bpy.types.Operator):
    bl_idname='sand3d.gallery'
    bl_label='Galerie : miniatures et aperçu au survol'
    bl_description='Galerie dans la vue 3D ; survol agrandi, clic pour sélectionner, Échap pour fermer'

    mode: bpy.props.EnumProperty(items=[('CURRENT','Actuel',''),('LIST','Liste détaillée',''),('SMALL','Petites vignettes',''),('LARGE','Grandes vignettes','')],default='CURRENT')

    def dimensions(self):
        state=bpy.context.window_manager.sand3d_state
        width,height=visible_width(self.region,getattr(self,'area',None)),self.region.height
        grid=max(116,width-min(360,width*0.38)-95)
        pitch=32 if state.view_mode=='LIST' else 192 if state.view_mode=='LARGE' else 116
        cellheight=32 if state.view_mode=='LIST' else pitch+9
        cols=1 if state.view_mode=='LIST' else max(1,int(grid//pitch))
        rows=max(1,int((height-125)//cellheight))
        return width,height,cols,rows,pitch,cellheight,grid

    def geometry(self):
        return self.dimensions()[:4]

    def hit(self,x,y):
        width,height,cols,rows,pitch,cellheight,grid=self.dimensions()
        listed=bpy.context.window_manager.sand3d_state.view_mode=='LIST'
        col=0 if listed else int((x-65)//pitch)
        row=int((height-100-y)//cellheight)
        index=self.offset+row*cols+col
        right=65+grid if listed else 65+cols*pitch
        state=bpy.context.window_manager.sand3d_state
        return index if 65<=x<right and 0<=col<cols and 0<=row<rows and index<len(state.results) else -1

    def invoke(self,context,event):
        global ACTIVE
        state=context.window_manager.sand3d_state
        if self.mode!='CURRENT':
            state.view_mode=self.mode
        if ACTIVE is not None:
            if ACTIVE.area==context.area:
                ACTIVE.offset=0
                ACTIVE.hover=-1
                ACTIVE.area.tag_redraw()
                return {'CANCELLED'}
            ACTIVE.finish(context)
        if context.area is None or context.area.type!='VIEW_3D':
            return {'CANCELLED'}
        self.area=context.area
        self.closed=False
        self.region=next(r for r in self.area.regions if r.type=='WINDOW')
        self.offset=0
        self.hover=-1
        self.textures={}
        self.handler=bpy.types.SpaceView3D.draw_handler_add(self.draw_overlay,(), 'WINDOW','POST_PIXEL')
        self.timer=context.window_manager.event_timer_add(0.1,window=context.window)
        ACTIVE=self
        context.window_manager.modal_handler_add(self)
        self.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def draw_preview(self,item,x,y,w,h):
        preview=thumbnails.preview(item)
        if preview is None or not preview.image_size[0]:
            thumbnails.request(item)
            text(x+5,y+h/2,item.format.upper(),16)
            return
        key=thumbnails.cache_key(item)
        if key not in self.textures:
            if len(self.textures)>=48:
                self.textures.clear()
            pw,ph=preview.image_size
            buffer=gpu.types.Buffer('FLOAT',pw*ph*4,list(preview.image_pixels_float))
            self.textures[key]=gpu.types.GPUTexture((pw,ph),format='RGBA16F',data=buffer)
        texture=self.textures[key]
        ratio=min(w/texture.width,h/texture.height)
        draw_texture_2d(texture,(x+(w-texture.width*ratio)/2,y+(h-texture.height*ratio)/2),texture.width*ratio,texture.height*ratio)

    def draw_overlay(self):
        if bpy.context.area!=self.area:
            return
        state=bpy.context.window_manager.sand3d_state
        width,height,cols,rows,pitch,cellheight,grid=self.dimensions()
        self.offset=min(self.offset,max(0,((len(state.results)-1)//(cols*rows))*(cols*rows)))
        listed=state.view_mode=='LIST'
        gpu.state.blend_set('ALPHA')
        blf.enable(0,blf.CLIPPING)
        blf.clipping(0,10,10,width-10,height-10)
        try:
            rect(8,8,width-16,height-16,(0.045,0.05,0.06,0.97))
            if width<580 or height<320:
                text(22,height-50,'Agrandir la vue ou réduire le panneau latéral.',12)
                text(22,height-75,'Échap : fermer la galerie.',12)
                return
            text(160,height-50,'POWER IMPORTER — Survol : aperçu · Clic : sélectionner · Molette : page · Échap : fermer')
            for n,(mode,label) in enumerate((('LIST','Liste détaillée'),('SMALL','Petites vignettes'),('LARGE','Grandes vignettes'))):
                x=65+n*150
                rect(x,height-88,144,25,(0.15,0.27,0.36,1) if state.view_mode==mode else (0.13,0.14,0.16,1))
                text(x+7,height-80,label,11)
            for slot,index in enumerate(range(self.offset,min(len(state.results),self.offset+cols*rows))):
                col,row=slot%cols,slot//cols
                x,y=65+col*pitch,height-100-(row+1)*cellheight
                item=state.results[index]
                name=item.relative_path.replace('\\','/').rsplit('/',1)[-1]
                w=grid if listed else pitch-8
                rect(x,y,w,cellheight-7,(0.15,0.27,0.36,1) if index==state.selected else (0.1,0.11,0.13,1))
                if listed:
                    text(x+5,y+8,name[:max(8,int((w-150)/7))],11)
                    text(x+max(80,w-145),y+8,item.format.upper()+' · '+item.size_text,10)
                else:
                    self.draw_preview(item,x+4,y+28,w-8,cellheight-40)
                    text(x+4,y+9,name[:max(10,int((w-8)/7))],11)
            index=self.hover if 0<=self.hover<len(state.results) else state.selected
            px=80+(grid if listed else cols*pitch)
            if 0<=index<len(state.results):
                item=state.results[index]
                self.draw_preview(item,px,150,max(50,width-px-25),max(60,height-270))
                text(px,120,item.relative_path.replace('\\','/').rsplit('/',1)[-1][:50])
                text(px,95,'Format : '+item.format.upper()+' · '+item.size_text)
                text(px,70,item.library_name[:50],11)
                text(px,45,item.relative_path[:60],10)
            text(65,22,f'{state.total} résultat(s) · lot {state.page}/{state.page_count} · vue {self.offset//(cols*rows)+1}/{max(1,(len(state.results)+cols*rows-1)//(cols*rows))}',11)
        finally:
            blf.disable(0,blf.CLIPPING)
            gpu.state.blend_set('NONE')

    def modal(self,context,event):
        if self.closed:
            return {'CANCELLED'}
        if not any(area==self.area for area in context.screen.areas) or event.type=='ESC':
            self.finish(context)
            return {'CANCELLED'}
        x,y=event.mouse_x-self.region.x,event.mouse_y-self.region.y
        width,height,cols,rows=self.geometry()
        inside=0<=x<width and 0<=y<height
        if inside and (width<580 or height<320):
            return {'RUNNING_MODAL'}
        state=context.window_manager.sand3d_state
        if inside and event.type=='LEFTMOUSE' and event.value=='PRESS' and height-88<=y<=height-63 and 65<=x<515:
            state.view_mode=('LIST','SMALL','LARGE')[int((x-65)//150)]
            self.offset=0
            self.hover=-1
            self.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if inside and event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'}:
            step=cols*rows
            count=len(state.results)
            candidate=self.offset+(step if event.type=='WHEELDOWNMOUSE' else -step)
            if candidate>=count and state.page<state.page_count:
                state.page+=1
                self.offset=0
            elif candidate<0 and state.page>1:
                state.page-=1
                self.offset=max(0,((len(state.results)-1)//step)*step)
            else:
                self.offset=max(0,min(max(0,((count-1)//step)*step),candidate))
            self.hover=-1
            self.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type=='MOUSEMOVE' and inside:
            self.hover=self.hit(x,y)
            self.area.tag_redraw()
        if event.type=='LEFTMOUSE' and event.value=='PRESS' and inside:
            self.hover=self.hit(x,y)
            if self.hover>=0:
                state.selected=self.hover
            return {'RUNNING_MODAL'}
        if event.type=='TIMER':
            self.area.tag_redraw()
        return {'RUNNING_MODAL'} if inside else {'PASS_THROUGH'}

    def finish(self,context):
        global ACTIVE
        self.closed=True
        if getattr(self,'handler',None):
            bpy.types.SpaceView3D.draw_handler_remove(self.handler,'WINDOW')
            self.handler=None
        if getattr(self,'timer',None):
            context.window_manager.event_timer_remove(self.timer)
            self.timer=None
        self.textures.clear()
        try:
            self.area.tag_redraw()
        except ReferenceError:
            pass
        if ACTIVE is self:
            ACTIVE=None

    def cancel(self,context):
        self.finish(context)


def register():
    bpy.utils.register_class(S3D_OT_gallery)


def unregister():
    if ACTIVE is not None:
        ACTIVE.finish(bpy.context)
    bpy.utils.unregister_class(S3D_OT_gallery)
