import bpy
import bpy_extras
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

up = Vector((0,0,1))
right = Vector((1,0,0))
front = Vector((0,1,0))

############## DRAW ###############

# DRAW VIEW 3D ###########

lineshader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')

now = None
past = None
valid = False

acceleration = None
speed0 = None

fps = 30
gravity = None

def view3d_pre_view():
    global acceleration,speed0,now,past,fps,valid,gravity
    C = bpy.context
    D = bpy.data

    fps = C.scene.render.fps / C.scene.render.fps_base
    gravity = C.scene.gravity
    
    now = C.active_object
    if now:
        past = D.objects.get(C.object.name+'_past')
        if past:
            speed0 = (now.matrix_world.translation - past.matrix_world.translation)*fps

        future = D.objects.get(C.object.name+'_future')
        if future:    
            speed1 = (future.matrix_world.translation - now.matrix_world.translation)*fps

        valid = future and past
        if valid:
            acceleration = (speed1 - speed0)*fps
    else:
        pass


# ACCELERATION #
def draw_acceleration_vector():
    if valid:
        coords = [
        now.matrix_world.translation, 
        now.matrix_world.translation + acceleration*props_container.view3d_scaling]
        
        gpu.state.blend_set('ALPHA')
        region = bpy.context.region
        lineshader.uniform_float("viewportSize", (region.width, region.height))
        lineshader.uniform_float("color", (1, 1, 0, 1))
        lineshader.uniform_float("lineWidth", 1)
        batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
        batch.draw(lineshader)  

def draw_acceleration_value():
    if valid:
        C = bpy.context
        font_id = 0
        pos = bpy_extras.view3d_utils.location_3d_to_region_2d(C.region, C.space_data.region_3d, C.active_object.matrix_world.translation, default=None)
        blf.position(font_id, pos.x, pos.y, 0)
        blf.size(font_id, 13.0)
        blf.color(font_id,1,1,0,1)
        blf.draw(font_id, str(round(acceleration.length,2))+" m/s²")
  
def draw_countergravity_vector():
    if valid:
        coords = [
        now.matrix_world.translation, 
        now.matrix_world.translation + (acceleration-gravity)*props_container.view3d_scaling]
        
        gpu.state.blend_set('ALPHA')
        region = bpy.context.region
        lineshader.uniform_float("viewportSize", (region.width, region.height))
        lineshader.uniform_float("color", (0.0, 0.5, 1, 1))
        lineshader.uniform_float("lineWidth", 1)
        batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
        batch.draw(lineshader)

# SPEED #
def draw_speed_vector():
    if past:    
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(1)
        coords = [
        now.matrix_world.translation, 
        now.matrix_world.translation + speed0*props_container.view3d_scaling]
        
        region = bpy.context.region
        lineshader.uniform_float("viewportSize", (region.width, region.height))
        lineshader.uniform_float("color", (0, 1, 1, 1))
        lineshader.uniform_float("lineWidth", 1)
        batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
        batch.draw(lineshader)
    
def draw_speed_value():
    if past:
        C = bpy.context
        font_id = 0
        pos = bpy_extras.view3d_utils.location_3d_to_region_2d(C.region, C.space_data.region_3d, C.active_object.matrix_world.translation, default=None)  
        blf.position(font_id, pos.x, pos.y, 0)
        blf.size(font_id, 13.0)
        blf.color(font_id,0,1,1,1)  
        blf.draw(font_id, str(round(speed0.length,2))+" m/s")

# DRAW GRAPH EDITOR ###########
    
def draw_acceleration_graph():
    C = bpy.context
    fcurve = C.active_editable_fcurve
    fps = C.scene.render.fps / C.scene.render.fps_base

    coords = []
    if fcurve is not None:
        for i in range(C.scene.frame_start,C.scene.frame_end): 
            speed0 = (fcurve.evaluate(i)-fcurve.evaluate(i-1))*fps
            speed1 = (fcurve.evaluate(i+1)-fcurve.evaluate(i))*fps
            acceleration = (speed1-speed0)*fps
            coords.append( (i,acceleration*props_container.graph_scaling) )
    
    gpu.state.blend_set('ALPHA')
    region = bpy.context.region
    lineshader.uniform_float("viewportSize", (region.width, region.height))
    lineshader.uniform_float("color",(1,0,0,0.5))
    #lineshader.uniform_float("lineWidth", 1)
    batch = batch_for_shader(lineshader,'LINE_STRIP',{"pos": coords})
    batch.draw(lineshader)

def draw_speed_graph():
    C = bpy.context
    fcurve = C.active_editable_fcurve
    fps = C.scene.render.fps / C.scene.render.fps_base
    
    coords = []
    if fcurve is not None:
        for i in range(C.scene.frame_start,C.scene.frame_end): 
            speed0 = (fcurve.evaluate(i)-fcurve.evaluate(i-1))*fps
            coords.append( (i,speed0*props_container.graph_scaling) )
    
    gpu.state.blend_set('ALPHA')
    region = bpy.context.region
    lineshader.uniform_float("viewportSize", (region.width, region.height))
    lineshader.uniform_float("color",(0,1,1,0.5))
    #lineshader.uniform_float("lineWidth", 1)
    batch = batch_for_shader(lineshader,'LINE_STRIP',{"pos": coords})
    batch.draw(lineshader)

############ DRAW HANDLERS ###############

def view3d_view_draw():
    if props_container.show_acceleration:
        draw_acceleration_vector()
    if props_container.show_speed:
        draw_speed_vector()
    if props_container.show_countergravity:
        draw_countergravity_vector()

def view3d_pixel_draw():
    if props_container.show_acceleration:
        draw_acceleration_value()
    if props_container.show_speed:
        draw_speed_value()

def graph_draw():
    if props_container.show_acceleration_graph:
        draw_acceleration_graph()
    if props_container.show_speed_graph:
        draw_speed_graph()
    
############## PROPERTIES ##################

class MovementInspectorSettingItem(bpy.types.PropertyGroup):
    # view 3d
    view3d_scaling: bpy.props.FloatProperty(name="Vectors scaling", default = 1.0,
                                                    description = "convenience scaling in viewport")
    
    show_acceleration: bpy.props.BoolProperty(name="Show acceleration", default = False)
    show_countergravity: bpy.props.BoolProperty(name="Show Countergravity", default = False, 
                                                description = "acceleration relative to gravity space-time, basically direction of standing")
    show_speed: bpy.props.BoolProperty(name="Show speed", default = False)
    # graph
    graph_scaling: bpy.props.FloatProperty(name="Graph scaling", default = 1.0,
                                           description = "convenience scaling in graph editor")

    show_acceleration_graph: bpy.props.BoolProperty(name="Show acceleration", default = False)
    show_speed_graph: bpy.props.BoolProperty(name="Show speed", default = False)

############### PANELS ################

class MotionViewPanel(bpy.types.Panel):
    bl_label = "Motion Inspector"
    bl_idname = "OBJECT_PT_motionpanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  'Animation'

    def draw(self, context):
        layout = self.layout
        global props_container
        props_container = context.window_manager.movement_inspector_overlays
        
        col = layout.column()
        #col.enabled = context.active_object and context.active_object.animation_data is not None
        col.prop(props_container,"view3d_scaling")
        col.prop(props_container,"show_countergravity")
        col.prop(props_container,"show_acceleration")
        col.prop(props_container,"show_speed")
        
        col = layout.column(align = True)
        col.operator("object.setup_frame_references")
        col.operator("object.clear_frame_references")
        
class FcurveMotionViewPanel(bpy.types.Panel):
    bl_label = "F-Curve Inspector"
    bl_idname = "OBJECT_PT_Fcurveinspector"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'F-Curve'
    
    def draw(self,context):
        layout = self.layout

        props_container = context.window_manager.movement_inspector_overlays

        
        layout.prop(props_container,"graph_scaling")
        layout.prop(props_container,"show_acceleration_graph")
        layout.prop(props_container,"show_speed_graph")

############### OPERATORS #################

class SetupFrameReferences(bpy.types.Operator):
    bl_idname = "object.setup_frame_references"
    bl_label = "Setup references"
    bl_description = "Duplicate object transforms and offset its animation to compare with current transform"
    
    @classmethod
    def poll(cls, context):
            try:
                return context.active_object.animation_data.action is not None
            except:
                return False
        
    def execute(self,context):
        C = context        
        D = bpy.data
        futurePostfix = C.object.name+'_future'
        pastPostfix = C.object .name+'_past'
        
        try:
            D.objects.remove(D.objects[futurePostfix])
            D.objects.remove(D.objects[pastPostfix])
        except:
            pass

        future = D.objects.new(futurePostfix,None)
        past = D.objects.new(pastPostfix,None)

        activeObjAction =  C.active_object.animation_data.action

        for obj in [future,past]:
            offset = -1 if obj.name == futurePostfix else +1
            obj.animation_data_create()
            #copy constraint
            for constraint in C.object.constraints:
                obj.constraints.copy( constraint )
            #link to scene
            C.scene.collection.objects.link(obj)
            obj.hide_set(True)
            #offset animation
            obj.animation_data.nla_tracks.new()
            obj.animation_data.nla_tracks[0].strips.new(
                activeObjAction.name ,
                int(activeObjAction.frame_range[0])+offset ,
                activeObjAction 
            )

        return {'FINISHED'}
    
# OPERATORS 2 #

class ClearFrameReferences(bpy.types.Operator):
    bl_idname = "object.clear_frame_references"
    bl_label = "Clear references"
    
    @classmethod
    def poll (cls,context):
        if context.active_object:
            futurePostfix = context.object.name+'_future'
            pastPostfix = context.object.name+'_past'
            D = bpy.data
            check = D.objects.get(futurePostfix) or D.objects.get(pastPostfix)
            return context.active_object and check
        else:
            return False
    
    def execute(self,context):     
        futurePostfix = context.object.name+'_future'
        pastPostfix = context.object.name+'_past'

        D = bpy.data

        f = D.objects.get(futurePostfix)
        if f:
            D.objects.remove(f)

        p = D.objects.get(pastPostfix)
        if p:
            D.objects.remove(p)

        return {'FINISHED'}
        
################### REG #####################
view3d = bpy.types.SpaceView3D
graph = bpy.types.SpaceGraphEditor

view3d_pre_view_handler = None
view3d_post_view_handler = None
view3d_post_pixel_handler = None
graph_post_view_handler = None

def register():
    bpy.utils.register_class(MovementInspectorSettingItem)
    bpy.types.WindowManager.movement_inspector_overlays = bpy.props.PointerProperty(type=MovementInspectorSettingItem)
    global props_container
    props_container = bpy.context.window_manager.movement_inspector_overlays
    bpy.utils.register_class(SetupFrameReferences)
    bpy.utils.register_class(ClearFrameReferences)
    bpy.utils.register_class(MotionViewPanel)
    bpy.utils.register_class(FcurveMotionViewPanel)

    global view3d_post_view_handler,view3d_post_pixel_handler,graph_post_view_handler,view3d_pre_view_handler
    view3d_pre_view_handler = view3d.draw_handler_add(view3d_pre_view, (), 'WINDOW', 'POST_VIEW')
    view3d_post_view_handler = view3d.draw_handler_add(view3d_view_draw, (), 'WINDOW', 'POST_VIEW')
    view3d_post_pixel_handler = view3d.draw_handler_add(view3d_pixel_draw, (), 'WINDOW', 'POST_PIXEL')
    graph_post_view_handler = graph.draw_handler_add(graph_draw, (), 'WINDOW','POST_VIEW')


def unregister():
    bpy.utils.unregister_class(MovementInspectorSettingItem)
    bpy.utils.unregister_class(SetupFrameReferences)
    bpy.utils.unregister_class(ClearFrameReferences)
    bpy.utils.unregister_class(MotionViewPanel)
    bpy.utils.unregister_class(FcurveMotionViewPanel)

    view3d.draw_handler_remove(view3d_pre_view_handler,'WINDOW')
    view3d.draw_handler_remove(view3d_post_view_handler,'WINDOW')
    view3d.draw_handler_remove(view3d_post_pixel_handler,'WINDOW')
    graph.draw_handler_remove(graph_post_view_handler,'WINDOW')

if __name__ == "__main__":
    register()
    