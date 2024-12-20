import bpy
import bpy_extras
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

shader = gpu.shader.from_builtin('UNIFORM_COLOR')
lineshader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
up = Vector((0,0,1))
right = Vector((1,0,0))
front = Vector((0,1,0))


############## DRAW ###############

acceleration = None
def draw_acceleration_vector():
    global acceleration

    C = bpy.context
    D = bpy.data

    fps = C.scene.render.fps / C.scene.render.fps_base
    
    future = D.objects.get(C.object.name+'_future')
    past = D.objects.get(C.object.name+'_past')

    if future and past:
        now = C.active_object
        
        speed0 = (now.matrix_world.translation - past.matrix_world.translation)*fps
        speed1 = (future.matrix_world.translation - now.matrix_world.translation)*fps
        acceleration = (speed1 - speed0)*fps
        
        coords = [
        now.matrix_world.translation, 
        now.matrix_world.translation + acceleration]
        
        gpu.state.blend_set('ALPHA')
        region = bpy.context.region
        lineshader.uniform_float("viewportSize", (region.width, region.height))
        lineshader.uniform_float("color", (1, 1, 0, 1))
        lineshader.uniform_float("lineWidth", 1)
        batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
        batch.draw(lineshader)  

def draw_acceleration_value():
    global acceleration
    if acceleration:
        C = bpy.context
        font_id = 0
        pos = bpy_extras.view3d_utils.location_3d_to_region_2d(C.region, C.space_data.region_3d, C.active_object.matrix_world.translation, default=None)
        blf.position(font_id, pos.x, pos.y, 0)
        blf.size(font_id, 13.0)
        blf.color(font_id,1,1,0,1)
        blf.draw(font_id, str(round(acceleration.length,2))+" m/s²")
        acceleration = None
  
def draw_countergravity_vector():
    C = bpy.context
    D = bpy.data
    fps = C.scene.render.fps / C.scene.render.fps_base
    
    future = D.objects.get(C.object.name+'_future')
    past = D.objects.get(C.object.name+'_past')
    if future and past:
        now = C.active_object
        
        speed0 = (now.matrix_world.translation - past.matrix_world.translation)*fps
        speed1 = (future.matrix_world.translation - now.matrix_world.translation)*fps
        acceleration = (speed1 - speed0)*fps
        
        gravity = C.scene.gravity
    
        coords = [
        now.matrix_world.translation, 
        now.matrix_world.translation + (acceleration-gravity)]
        
        gpu.state.blend_set('ALPHA')
        region = bpy.context.region
        lineshader.uniform_float("viewportSize", (region.width, region.height))
        lineshader.uniform_float("color", (0.0, 0.5, 1, 1))
        lineshader.uniform_float("lineWidth", 1)
        batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
        batch.draw(lineshader)
    
speed0 = None
def draw_speed_vector():
    C = bpy.context
    D = bpy.data
    fps = C.scene.render.fps / C.scene.render.fps_base
    
    past = D.objects.get(C.object.name+'_past')

    if past:
        now = C.active_object
        global speed0
        speed0 = (now.matrix_world.translation - past.matrix_world.translation)*fps
        
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(1)
        coords = [
        now.matrix_world.translation, 
        now.matrix_world.translation + speed0]
        
        region = bpy.context.region
        lineshader.uniform_float("viewportSize", (region.width, region.height))
        lineshader.uniform_float("color", (0, 1, 1, 1))
        lineshader.uniform_float("lineWidth", 1)
        batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
        batch.draw(lineshader)
    
def draw_speed_value():
    global speed0
    if speed0:
        C = bpy.context
        font_id = 0
        pos = bpy_extras.view3d_utils.location_3d_to_region_2d(C.region, C.space_data.region_3d, C.active_object.matrix_world.translation, default=None)  
        blf.position(font_id, pos.x, pos.y, 0)
        blf.size(font_id, 13.0)
        blf.color(font_id,0,1,1,1)  
        blf.draw(font_id, str(round(speed0.length,2))+" m/s")
        speed0 = None

# DRAW HANDLERS GRAPH EDITOR #
    
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
            coords.append( (i,acceleration) )
    
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
    for i in range(C.scene.frame_start,C.scene.frame_end): 
        speed0 = (fcurve.evaluate(i)-fcurve.evaluate(i-1))*fps
        coords.append( (i,speed0) )
    
    gpu.state.blend_set('ALPHA')
    region = bpy.context.region
    lineshader.uniform_float("viewportSize", (region.width, region.height))
    lineshader.uniform_float("color",(0,1,1,0.5))
    #lineshader.uniform_float("lineWidth", 1)
    batch = batch_for_shader(lineshader,'LINE_STRIP',{"pos": coords})
    batch.draw(lineshader)
    
############## PROPERTIES ##################

props_container = bpy.types.WindowManager
space = bpy.types.SpaceView3D
graph = bpy.types.SpaceGraphEditor

def toggleAccelerationOverlay(self,context):
    panel = MotionViewPanel
    if self.show_acceleration:
        panel.acceleration_handler = space.draw_handler_add(draw_acceleration_vector, (), 'WINDOW', 'POST_VIEW')
        panel.acceleration_text_Handler = space.draw_handler_add(draw_acceleration_value, (), 'WINDOW', 'POST_PIXEL')
    else:
        space.draw_handler_remove(panel.acceleration_handler,'WINDOW')
        space.draw_handler_remove(panel.acceleration_text_Handler,'WINDOW')  

def toggleSpeedOverlay(self,context):
    panel = MotionViewPanel
    if self.show_speed:
        panel.speed_handler = space.draw_handler_add(draw_speed_vector, (), 'WINDOW', 'POST_VIEW')
        panel.speed_text_handler = space.draw_handler_add(draw_speed_value, (), 'WINDOW', 'POST_PIXEL')
    else:
        space.draw_handler_remove(panel.speed_handler,'WINDOW')
        space.draw_handler_remove(panel.speed_text_handler,'WINDOW')

def toggleCountergravityOverlay(self,context):
    panel = MotionViewPanel
    if self.show_countergravity:
        panel.countergravity_handler = space.draw_handler_add(draw_countergravity_vector, (), 'WINDOW', 'POST_VIEW')
    else:
        space.draw_handler_remove(panel.countergravity_handler,'WINDOW')    

# PROPERTIES GRAPH EDITOR #
def toggleAccelerationGraph(self,context):
    panel = FcurveMotionViewPanel
    if self.show_acceleration_graph:
        panel.acceleration_handler = graph.draw_handler_add(draw_acceleration_graph, (), 'WINDOW','POST_VIEW')
    else:
        panel.acceleration_handler = graph.draw_handler_remove(panel.acceleration_handler, 'WINDOW')

def toggleSpeedGraph(self,context):
    panel = FcurveMotionViewPanel
    if self.show_speed_graph:
        panel.speed_handler = graph.draw_handler_add(draw_speed_graph, (), 'WINDOW','POST_VIEW')
    else:
        panel.speed_handler = graph.draw_handler_remove(panel.speed_handler, 'WINDOW')

class MovementInspectorSettingItem(bpy.types.PropertyGroup):
    # view 3d
    show_acceleration: bpy.props.BoolProperty(name="Show acceleration", update = toggleAccelerationOverlay, default = False)
    show_countergravity: bpy.props.BoolProperty(name="Show Countergravity", update = toggleCountergravityOverlay, default = False, 
        description = "acceleration relative to gravity space-time, basically direction of standing")
    show_speed: bpy.props.BoolProperty(name="Show speed", update = toggleSpeedOverlay, default = False)
    # graph
    show_acceleration_graph: bpy.props.BoolProperty(name="Show acceleration", update = toggleAccelerationGraph, default = False)
    show_speed_graph: bpy.props.BoolProperty(name="Show speed", update = toggleSpeedGraph, default = False)

############### PANELS ################

class MotionViewPanel(bpy.types.Panel):
    bl_label = "Motion Inspector"
    bl_idname = "OBJECT_PT_motionpanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  'Animation'
    
    acceleration_handler = None
    acceleration_text_Handler = None
    countergravity_handler = None
    speed_handler = None
    speed_text_handler = None

    def draw(self, context):
        layout = self.layout

        props_container = context.window_manager.movement_inspector_overlays
        
        col = layout.column()
        #col.enabled = context.active_object and context.active_object.animation_data is not None
        col.prop(props_container,"show_acceleration")
        col.prop(props_container,"show_speed")
        col.prop(props_container,"show_countergravity")
        
        col = layout.column(align = True)
        col.operator("object.setup_frame_references")
        col.operator("object.clear_frame_references")
        
class FcurveMotionViewPanel(bpy.types.Panel):
    bl_label = "F-Curve Inspector"
    bl_idname = "OBJECT_PT_Fcurveinspector"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'F-Curve'
    
    acceleration_handler = None
    speed_handler = None
    
    def draw(self,context):
        layout = self.layout

        props_container = context.window_manager.movement_inspector_overlays

        layout.prop(props_container,"show_acceleration_graph")
        layout.prop(props_container,"show_speed_graph")

############### OPERATORS #################

class SetupFrameReferences(bpy.types.Operator):
    bl_idname = "object.setup_frame_references"
    bl_label = "Setup references"
    bl_description = "Duplicate object transforms and offset its animation to compare with current transform"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.animation_data is not None
        
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

def register():
    bpy.utils.register_class(MovementInspectorSettingItem)
    props_container.movement_inspector_overlays = bpy.props.PointerProperty(type=MovementInspectorSettingItem)
    bpy.utils.register_class(SetupFrameReferences)
    bpy.utils.register_class(ClearFrameReferences)
    bpy.utils.register_class(MotionViewPanel)
    bpy.utils.register_class(FcurveMotionViewPanel)


def unregister():
    bpy.utils.unregister_class(MovementInspectorSettingItem)
    bpy.utils.unregister_class(SetupFrameReferences)
    bpy.utils.unregister_class(ClearFrameReferences)
    bpy.utils.unregister_class(MotionViewPanel)
    bpy.utils.unregister_class(FcurveMotionViewPanel)

if __name__ == "__main__":
    register()
    