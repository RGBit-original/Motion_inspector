import bpy
import bpy_extras
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

up = Vector((0,0,1))
right = Vector((1,0,0))
front = Vector((0,1,0))

############################################
############# ADDON PREFERENCES ############
############################################

class MotionInspectorPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def view3d_update_category(self,context):
        try:
            bpy.utils.unregister_class(MotionViewPanel)
        except:
            pass

        MotionViewPanel.bl_category = self.view3d_sidebar_category
        bpy.utils.register_class(MotionViewPanel)

    def graph_update_category(self,context):
        try:
            bpy.utils.unregister_class(FcurveMotionViewPanel)
        except:
            pass

        FcurveMotionViewPanel.bl_category = self.graph_sidebar_category
        bpy.utils.register_class(FcurveMotionViewPanel)

    view3d_sidebar_category: bpy.props.StringProperty(
        name = "Category name",
        description = "Set sidebar category name. You can type in name of the existing category and panel will be added there, instead of creating new category",
        default = "Animation",
        update = view3d_update_category
    )

    graph_sidebar_category: bpy.props.StringProperty(
        name = "Category name",
        description = "Set sidebar category name. You can type in name of the existing category and panel will be added there, instead of creating new category",
        default = "F-Curve",
        update = graph_update_category
    )

    def draw(self,context):
        layout = self.layout
        # layout.use_property_split = True
        # layout.use_property_decorate = False

        layout.label(text = "3D View panel :")

        row = layout.row(align = True)
        row.alignment= 'LEFT'
        row.label(text = "Show in ")
        row.prop(self, "view3d_sidebar_category",text = "")
        row.label(text = " sidebar category")

        layout.label(text = "Graph editor panel :")

        row = layout.row(align = True)
        row.alignment= 'LEFT'
        row.label(text = "Show in ")
        row.prop(self, "graph_sidebar_category",text = "")
        row.label(text = " sidebar category")

###################################
############# COMPUTE #############
###################################

now_position = None

valid = False
acceleration = None
speed0 = None

fps = 30
gravity = None

def compute_global_values():
    global acceleration,speed0,now_position,valid
    global fps, gravity
    C = bpy.context
    D = bpy.data

    fps = C.scene.render.fps / C.scene.render.fps_base
    gravity = C.scene.gravity
    
    # compute object movement
    now = C.active_object
    bone = C.active_pose_bone
    if now:
        if bone is not None:
            past = D.objects.get(now.name+'_past')
            future = D.objects.get(now.name+'_future')
            valid = future and past

            # converts only rotations, not translations, idk why
            world_now = now.convert_space(pose_bone=None, matrix=bone.matrix, from_space='LOCAL', to_space='WORLD')
            world_past = past.convert_space(pose_bone=None, matrix=past.pose.bones[bone.name].matrix, from_space='LOCAL', to_space='WORLD')
            world_future = future.convert_space(pose_bone=None, matrix=future.pose.bones[bone.name].matrix, from_space='LOCAL', to_space='WORLD')

            now_translation = world_now.translation + now.matrix_world.translation
            past_translation = world_past.translation + past.matrix_world.translation
            future_translation = world_future.translation + future.matrix_world.translation

            #pass to global
            now_position = now_translation

            if past:
                speed0 = (now_translation - past_translation)*fps
            if future:    
                speed1 = (future_translation - now_translation)*fps
            if valid:
                acceleration = (speed1 - speed0)*fps
        else:
            past = D.objects.get(now.name+'_past')
            future = D.objects.get(now.name+'_future')
            valid = future and past

            now_position = now.matrix_world.translation
            
            if past:
                speed0 = (now.matrix_world.translation - past.matrix_world.translation)*fps
            if future:    
                speed1 = (future.matrix_world.translation - now.matrix_world.translation)*fps
            if valid:
                acceleration = (speed1 - speed0)*fps
    else:
        pass

# ############################################################
# class MovementInspectorObjectData(bpy.types.PropertyGroup):
#     past: bpy.props.PointerProperty(type = bpy.types.Object)
#     future: bpy.props.PointerProperty(type = bpy.types.Object)
    
#     speed: bpy.props.FloatVectorProperty()
#     acceleration: bpy.props.FloatVectorProperty()
# ############################################################

###################################
############## DRAW ###############
###################################

lineshader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')

def draw_line(color,width,coords):
    gpu.state.blend_set('ALPHA')
    region = bpy.context.region
    lineshader.uniform_float("viewportSize", (region.width, region.height))
    lineshader.uniform_float("color", color)
    if width:
        lineshader.uniform_float("lineWidth", width)
    batch = batch_for_shader(lineshader, 'LINES', {"pos": coords})
    batch.draw(lineshader)  

def draw_line_strip(color,coords):
    gpu.state.blend_set('ALPHA')
    region = bpy.context.region
    lineshader.uniform_float("viewportSize", (region.width, region.height))
    lineshader.uniform_float("color",color)
    #lineshader.uniform_float("lineWidth", 1)
    batch = batch_for_shader(lineshader,'LINE_STRIP',{"pos": coords})
    batch.draw(lineshader)

def draw_value(value,units,color,x,y):
    font_id = 0
    blf.position(font_id, x, y, 0)
    blf.size(font_id, 13.0)
    blf.color(font_id,color[0],color[1],color[2],color[3])
    blf.draw(font_id, str(round(value,2))+units)

# FOR VIEW 3D #############

def draw_object_vector(startpos, vector, color):
    ''' draw from origin of object '''
    if valid:
        coords = [
                startpos,
                startpos + vector*props_container.view3d_scaling]

        draw_line(color,1,coords)

def draw_object_value(startpos, value, units, color, offsetX, offsetY):
    ''' draw value on object '''
    if valid:
        C = bpy.context
        pos = bpy_extras.view3d_utils.location_3d_to_region_2d(C.region, C.space_data.region_3d, startpos, default=None)

        draw_value(value," "+units,color,pos.x + offsetX,pos.y + offsetY)

# FOR GRAPH EDITOR ###########

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
    
    draw_line_strip((1,0,0,0.5),coords)

def draw_speed_graph():
    C = bpy.context
    fcurve = C.active_editable_fcurve
    fps = C.scene.render.fps / C.scene.render.fps_base
    
    coords = []
    if fcurve is not None:
        for i in range(C.scene.frame_start,C.scene.frame_end): 
            speed0 = (fcurve.evaluate(i)-fcurve.evaluate(i-1))*fps
            coords.append( (i,speed0*props_container.graph_scaling) )
    
    draw_line_strip((0,1,1,0.5),coords)

###########################################
############ DRAW CALLBACKS ###############
###########################################

def view3d_pre_view():
    compute_global_values()

def view3d_view_draw():
    if props_container.show_acceleration:
        draw_object_vector(now_position,acceleration,(1,1,0,1))
    if props_container.show_speed:
        draw_object_vector(now_position,speed0,(0,1,1,1))
    if props_container.show_countergravity:
        draw_object_vector(now_position,acceleration-gravity,(0,0.5,1,1))

def view3d_pixel_draw():
    if props_container.show_acceleration:
        draw_object_value(now_position, acceleration.length,"m/s²", (1,1,0,1), 0, 0)
    if props_container.show_speed:
        draw_object_value(now_position, speed0.length,"m/s", (0,1,1,1), 0, -13)
    if props_container.show_countergravity:
        dimensions = blf.dimensions(0, str(round((acceleration-gravity).length,2))+" m/s²")
        draw_object_value(now_position, (acceleration-gravity).length,"m/s²",(0,0.5,1,1),-dimensions[0],0)

def graph_draw():
    if props_container.show_acceleration_graph:
        draw_acceleration_graph()
    if props_container.show_speed_graph:
        draw_speed_graph()

##################################################### 
################## DRAW LAYER ENABLE ################
#####################################################

view3d = bpy.types.SpaceView3D
graph = bpy.types.SpaceGraphEditor

view3d_pre_view_handler = None
view3d_post_view_handler = None
view3d_post_pixel_handler = None
graph_post_view_handler = None

def view3d_toggle(self,context):
    global view3d_post_view_handler,view3d_post_pixel_handler,view3d_pre_view_handler
    if self.view3d_enable:
        view3d_pre_view_handler = view3d.draw_handler_add(view3d_pre_view, (), 'WINDOW', 'PRE_VIEW')
        view3d_post_view_handler = view3d.draw_handler_add(view3d_view_draw, (), 'WINDOW', 'POST_VIEW')
        view3d_post_pixel_handler = view3d.draw_handler_add(view3d_pixel_draw, (), 'WINDOW', 'POST_PIXEL')
    else:
        view3d.draw_handler_remove(view3d_pre_view_handler,'WINDOW')
        view3d.draw_handler_remove(view3d_post_view_handler,'WINDOW')
        view3d.draw_handler_remove(view3d_post_pixel_handler,'WINDOW')

def graph_toggle(self,context):
    global graph_post_view_handler
    if self.graph_enable:
        graph_post_view_handler = graph.draw_handler_add(graph_draw, (), 'WINDOW','POST_VIEW')
    else:
        graph.draw_handler_remove(graph_post_view_handler,'WINDOW')

############################################
############## PROPERTIES ##################
############################################

class MovementInspectorSettingItem(bpy.types.PropertyGroup):
    # view 3d
    view3d_enable: bpy.props.BoolProperty(name = "",update = view3d_toggle, default = False)

    view3d_scaling: bpy.props.FloatProperty(name="Vectors scaling", default = 1.0,
                                                    description = "convenience scaling in viewport")
    
    show_acceleration: bpy.props.BoolProperty(name="Show acceleration", default = False)
    show_countergravity: bpy.props.BoolProperty(name="Show countergravity", default = False, 
                                                description = "difference from freefall, basically direction of standing")
    show_speed: bpy.props.BoolProperty(name="Show speed", default = False)
    # graph
    graph_enable: bpy.props.BoolProperty(name = "",update = graph_toggle, default = False)

    graph_scaling: bpy.props.FloatProperty(name="Graph scaling", default = 1.0,
                                           description = "convenience scaling in graph editor")

    show_acceleration_graph: bpy.props.BoolProperty(name="Show acceleration", default = False)
    show_speed_graph: bpy.props.BoolProperty(name="Show speed", default = False)

#######################################
############### PANELS ################
#######################################

class MotionViewPanel(bpy.types.Panel):
    bl_label = "Motion Inspector"
    bl_idname = "OBJECT_PT_motionpanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category =  'Animation'

    def draw_header(self,context):
        layout = self.layout
        layout.prop(props_container,"view3d_enable")

    def draw(self, context):
        layout = self.layout
        
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
    
    def draw_header(self,context):
        layout = self.layout
        layout.prop(props_container,"graph_enable")

    
    def draw(self,context):
        layout = self.layout
        
        layout.prop(props_container,"graph_scaling")
        layout.prop(props_container,"show_acceleration_graph")
        layout.prop(props_container,"show_speed_graph")

###########################################
############### OPERATORS #################
###########################################

class SetupFrameReferences(bpy.types.Operator):
    bl_idname = "object.setup_frame_references"
    bl_label = "Setup references"
    bl_description = "Duplicate object transforms and offset its animation to compare with current transform (if something wrong, click again)"
    
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
        pastPostfix = C.object.name+'_past'
        
        f = D.objects.get(futurePostfix)
        p = D.objects.get(pastPostfix)

        if f: D.objects.remove(f)
        if p: D.objects.remove(p)

        is_armature = C.object.type == 'ARMATURE'
        activeObjAction =  C.active_object.animation_data.action    

        if is_armature:
            future = C.object.copy()
            future.name = futurePostfix
            past = C.object.copy()
            past.name = pastPostfix

            for obj in [future,past]:
                offset = -1 if obj.name == futurePostfix else +1
                #offset animation
                obj.animation_data.action = None
                obj.animation_data.nla_tracks.new()
                obj.animation_data.nla_tracks[0].strips.new(
                    activeObjAction.name ,
                    int(activeObjAction.frame_range[0])+offset ,
                    activeObjAction 
                )
                #link to scene
                C.scene.collection.objects.link(obj)
                obj.hide_set(True)

        else:
            future = D.objects.new(futurePostfix,None)
            past = D.objects.new(pastPostfix,None)

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
        p = D.objects.get(pastPostfix)

        if f: D.objects.remove(f)
        if p: D.objects.remove(p)

        return {'FINISHED'}

#############################################
################### REG #####################
#############################################

classes = [
    MovementInspectorSettingItem,
    SetupFrameReferences,
    ClearFrameReferences,
    MotionViewPanel,
    FcurveMotionViewPanel,
    MotionInspectorPreferences
]

def register():
    
    for cls in classes:
        bpy.utils.register_class(cls)

    MotionInspectorPreferences.view3d_update_category(bpy.context.preferences.addons[__package__].preferences,bpy.context)
    MotionInspectorPreferences.graph_update_category(bpy.context.preferences.addons[__package__].preferences,bpy.context)

    bpy.types.WindowManager.movement_inspector_overlays = bpy.props.PointerProperty(type=MovementInspectorSettingItem)
    global props_container
    props_container = bpy.context.window_manager.movement_inspector_overlays

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.movement_inspector_overlays

if __name__ == "__main__":
    register()
    