import bpy
import math # ← ポイント1：数学モジュールが必要
import mathutils
import bpy_extras
import gpu
import gpu_extras.batch
import copy

# 1. アドオン情報
bl_info = {
    "name": "レベルエディタ",
    "author": "Taro Kamata",
    "version": (1, 0),
    "blender": (3, 3, 1),
    "category": "Object"
}

# --- オペレータ1: 頂点を伸ばす ---
class MYADDON_OT_stretch_vertex(bpy.types.Operator):
    bl_idname = "object.myaddon_ot_stretch_vertex"
    bl_label = "頂点を伸ばす"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if "Cube" in bpy.data.objects:
            bpy.data.objects["Cube"].data.vertices[0].co.x += 1.0
            print("頂点を伸ばしました。びろーん ✨")
        return {'FINISHED'}

# --- オペレータ2: ICO球生成 ---
class MYADDON_OT_create_ico_sphere(bpy.types.Operator):
    bl_idname = "object.myaddon_ot_create_ico_sphere"
    bl_label = "ICO球生成"
    bl_description = "ICO球を生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_ico_sphere_add()
        print("ICO球を生成しました。🌕")
        return {'FINISHED'}

# --- オペレータ: コライダー追加 ---
class MYADDON_OT_add_collider(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_add_collider"
    bl_label = "コライダー 追加"
    bl_description = "['collider']カスタムプロパティを追加します"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # ['collider']カスタムプロパティを追加
        context.object["collider"] = "BOX"
        context.object["collider_center"] = mathutils.Vector((0,0,0))
        context.object["collider_size"] = mathutils.Vector((2,2,2))
        return {"FINISHED"}

# --- パネル: コライダー ---
class OBJECT_PT_collider(bpy.types.Panel):
    bl_idname = "OBJECT_PT_collider"
    bl_label = "Collider"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    # サブメニューの描画
    def draw(self, context):
        # パネルに項目を追加
        if "collider" in context.object:
            # 既にプロパティがあれば、プロパティを表示
            self.layout.prop(context.object, '["collider"]', text="Type")
            self.layout.prop(context.object, '["collider_center"]', text="Center")
            self.layout.prop(context.object, '["collider_size"]', text="Size")
        else:
            # プロパティがなければ、プロパティ追加ボタンを表示
            self.layout.operator(MYADDON_OT_add_collider.bl_idname)

# --- 描画処理: コライダー ---
class DrawCollider:
    handle = None

    def draw_collider():
        vertices = {"pos": []}
        indices = []
        
        # offsets for the 8 vertices of a box
        offsets = [
            [-0.5, -0.5, -0.5], # 0
            [ 0.5, -0.5, -0.5], # 1
            [ 0.5,  0.5, -0.5], # 2
            [-0.5,  0.5, -0.5], # 3
            [-0.5, -0.5,  0.5], # 4
            [ 0.5, -0.5,  0.5], # 5
            [ 0.5,  0.5,  0.5], # 6
            [-0.5,  0.5,  0.5], # 7
        ]
        
        # iterate over all objects in the current scene
        for object in bpy.context.scene.objects:
            # skip drawing if the object doesn't have a collider property
            if not "collider" in object:
                continue
                
            center = mathutils.Vector((0,0,0))
            size = mathutils.Vector((2,2,2))
            
            center[0]=object["collider_center"][0]
            center[1]=object["collider_center"][1]
            center[2]=object["collider_center"][2]
            size[0]=object["collider_size"][0]
            size[1]=object["collider_size"][1]
            size[2]=object["collider_size"][2]
            
            start = len(vertices["pos"])
            
            # calculate position for each vertex
            for offset in offsets:
                pos = copy.copy(center)
                pos[0]+=offset[0]*size[0]
                pos[1]+=offset[1]*size[1]
                pos[2]+=offset[2]*size[2]
                
                # convert from local coordinates to world coordinates
                pos = object.matrix_world @ pos
                vertices['pos'].append(pos)
                
            # append indices for the 12 edges of the box
            indices.extend([
                (start+0, start+1), (start+1, start+2), (start+2, start+3), (start+3, start+0),
                (start+4, start+5), (start+5, start+6), (start+6, start+7), (start+7, start+4),
                (start+0, start+4), (start+1, start+5), (start+2, start+6), (start+3, start+7)
            ])
            
        if len(vertices["pos"]) > 0:
            if bpy.app.version >= (4, 0, 0):
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            else:
                shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
            batch = gpu_extras.batch.batch_for_shader(shader, 'LINES', {"pos": vertices["pos"]}, indices=indices)
            shader.bind()
            shader.uniform_float("color", (0.5, 1.0, 0.5, 1.0)) # Draw green box
            batch.draw(shader)

# --- オペレータ3: シーン情報の走査と出力 ---
class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"
    # 出力するファイルの拡張子
    filename_ext = ".scene"

    def export(self):
        """ファイルに出力"""
        print("シーン情報出力開始... %r" % self.filepath)
        
        # ファイルをテキスト形式で書き出し用にオープン
        # スコープを抜けると自動的にクローズされる
        with open(self.filepath, "wt") as file:
            # ファイルに文字列を書き込む
            file.write("SCENE\n")
            
            for object in bpy.context.scene.objects:
                file.write(f"{object.type} - {object.name}\n")
                trans, rot, scale = object.matrix_local.decompose()
                rot = rot.to_euler()
                # math.degrees を使うために import math が必要
                rot_deg = (math.degrees(rot.x), math.degrees(rot.y), math.degrees(rot.z))
                
                file.write("  Trans(%f, %f, %f)\n" % (trans.x, trans.y, trans.z))
                file.write("  Rot  (%f, %f, %f)\n" % rot_deg)
                file.write("  Scale(%f, %f, %f)\n" % (scale.x, scale.y, scale.z))
                
                if object.parent:
                    file.write(f"  Parent: {object.parent.name}\n")
                
                # カスタムプロパティ'collider'
                if "collider" in object:
                    file.write(f"  C {object['collider']}\n")
                    temp_str = "  CC %f %f %f"
                    temp_str %= (object["collider_center"][0],object["collider_center"][1],object["collider_center"][2])
                    file.write(f"{temp_str}\n")
                    temp_str = "  CS %f %f %f"
                    temp_str %= (object["collider_size"][0],object["collider_size"][1],object["collider_size"][2])
                    file.write(f"{temp_str}\n")
                
                file.write("\n")

    def execute(self, context):
        print("シーン情報をExportします")

        # ファイルに出力
        self.export()

        self.report({'INFO'}, "シーン情報をExportしました")
        print("シーン情報をExportしました")

        return {'FINISHED'}

# --- サブメニュークラス ---
class TOPBAR_MT_my_menu(bpy.types.Menu):
    bl_idname = "TOPBAR_MT_my_menu"
    bl_label = "MyMenu"
    bl_description = "拡張メニュー by " + bl_info["author"]

    def draw(self, context):
        layout = self.layout
        layout.operator(MYADDON_OT_stretch_vertex.bl_idname, icon='VERTEXSEL')
        layout.operator(MYADDON_OT_create_ico_sphere.bl_idname, icon='MESH_ICOSPHERE')
        layout.operator(MYADDON_OT_export_scene.bl_idname, icon='EXPORT')
        # 区切り線
        layout.separator()
        # マニュアル項目
        layout.operator("wm.url_open_preset", text="Manual", icon='HELP')
        # 区切り線
        layout.separator()
        # メニュー削除ボタン
        layout.operator(MYADDON_OT_remove_menu.bl_idname, icon='CANCEL')

    def submenu(self, context):
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

# --- オペレータ: メニュー削除 ---
class MYADDON_OT_remove_menu(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_remove_menu"
    bl_label = "メニューを削除"
    bl_description = "トップバーからこのメニューを削除します"

    def execute(self, context):
        remove_my_menu()
        self.report({'INFO'}, "MyMenuを削除しました")
        return {'FINISHED'}

# 2. 登録するクラスのリスト
classes = (
    MYADDON_OT_stretch_vertex,
    MYADDON_OT_create_ico_sphere,
    MYADDON_OT_export_scene,
    MYADDON_OT_remove_menu,
    TOPBAR_MT_my_menu,
    MYADDON_OT_add_collider,
    OBJECT_PT_collider,
)

# 3. 有効化・無効化処理
def remove_my_menu():
    """既存のMyMenuサブメニューをトップバーから完全に全削除（重複防止）"""
    if hasattr(bpy.types.TOPBAR_MT_editor_menus, "_draw_funcs"):
        draw_funcs = bpy.types.TOPBAR_MT_editor_menus._draw_funcs
        to_remove = []
        for func in draw_funcs:
            name = getattr(func, "__name__", "")
            qualname = getattr(func, "__qualname__", "")
            func_str = str(func)
            
            # submenu, draw_menu_manual, TOPBAR_MT_my_menu 関連の関数をすべて検出
            if (name in ("submenu", "draw_menu_manual") or 
                "TOPBAR_MT_my_menu" in qualname or 
                "TOPBAR_MT_my_menu" in func_str or
                "my_menu" in name.lower()):
                to_remove.append(func)
        
        # 検出した関数を重複含めてすべて削除
        for func in to_remove:
            while func in draw_funcs:
                try:
                    draw_funcs.remove(func)
                except ValueError:
                    break
    else:
        try:
            bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_my_menu.submenu)
        except Exception:
            pass

def register():
    # 1. 既存のMyMenuをトップバーから削除（重複防止）
    remove_my_menu()

    # 2. すでに登録されているクラスがあれば安全に解除してから登録
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
        bpy.utils.register_class(cls)

    # 3. メニューに最新のMyMenuを追加
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_my_menu.submenu)
    
    # 4. 描画ハンドラの登録
    if DrawCollider.handle:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(DrawCollider.handle, 'WINDOW')
        except Exception:
            pass
        DrawCollider.handle = None
    DrawCollider.handle = bpy.types.SpaceView3D.draw_handler_add(DrawCollider.draw_collider, (), 'WINDOW', 'POST_VIEW')
    
    print("レベルエディタが有効化されました。")

def unregister():
    # 描画ハンドラの解除
    if DrawCollider.handle:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(DrawCollider.handle, 'WINDOW')
        except Exception:
            pass
        DrawCollider.handle = None

    # トップバーからMyMenuを全削除
    remove_my_menu()

    # クラスの登録解除
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
            
    print("レベルエディタが無効化されました。")

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()