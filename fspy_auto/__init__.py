bl_info = {
    "name":        "fSpy Auto",
    "author":      "David Bicho",
    "version":     (0, 1, 0),
    "blender":     (4, 0, 0),
    "location":    "View3D > N-panel > fSpy Auto",
    "description": "Automatisk kamerakalibrering från foto med AI",
    "category":    "Camera",
}

ADDON_VERSION = "v0.1.0"

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper


# ─── OPERATORS ────────────────────────────────────────────────────────────────

class FSPYAUTO_OT_import_photo(bpy.types.Operator, ImportHelper):
    """Välj ett foto och kalibrerar kameran automatiskt"""
    bl_idname = "fspyauto.import_photo"
    bl_label  = "Välj foto..."

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.webp",
        options={'HIDDEN'}
    )

    def execute(self, context):
        from . import inference

        self.report({'INFO'}, f"Analyserar {self.filepath}...")

        try:
            result = inference.run_inference(self.filepath)
            inference.apply_to_blender(result)

            # Spara resultat i scene properties för att visa i panelen
            context.scene.fspyauto_last_fov   = f"{result['fov_degrees']:.1f}°"
            context.scene.fspyauto_last_pitch = f"{result['pitch_degrees']:.1f}°"
            context.scene.fspyauto_last_roll  = f"{result['roll_degrees']:.1f}°"
            context.scene.fspyauto_last_yaw   = f"{result['yaw_degrees']:.1f}°"

            self.report({'INFO'}, "Kamera kalibrerad!")

        except Exception as e:
            self.report({'ERROR'}, str(e))

        return {'FINISHED'}


class FSPYAUTO_OT_update_model(bpy.types.Operator):
    """Ladda ner eller uppdatera AI-modellen från GitHub"""
    bl_idname = "fspyauto.update_model"
    bl_label  = "Uppdatera modell"

    def execute(self, context):
        from .downloader import ensure_model, get_local_model_version

        self.report({'INFO'}, "Kollar efter uppdateringar...")
        status, message = ensure_model(force=True)

        if status == "ok":
            version = get_local_model_version() or "okänd"
            context.scene.fspyauto_model_version = version
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)

        return {'FINISHED'}


# ─── PANEL ────────────────────────────────────────────────────────────────────

class FSPYAUTO_PT_panel(bpy.types.Panel):
    bl_label      = "fSpy Auto"
    bl_idname     = "FSPYAUTO_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category   = "fSpy Auto"

    def draw(self, context):
        layout = self.layout
        scene  = context.scene

        # ── Versioner ──
        box = layout.box()
        box.label(text=f"Addon:  {ADDON_VERSION}", icon='BLENDER')
        mv = scene.fspyauto_model_version
        box.label(text=f"Modell: {mv if mv else 'ej nedladdad'}", icon='NETWORK_DRIVE')

        layout.separator()

        # ── Importknapp ──
        layout.operator("fspyauto.import_photo", icon='IMAGE_DATA')

        layout.separator()

        # ── Senaste resultat ──
        if scene.fspyauto_last_fov:
            box = layout.box()
            box.label(text="Senaste kalibrering:", icon='CAMERA_DATA')
            box.label(text=f"FOV:   {scene.fspyauto_last_fov}")
            box.label(text=f"Pitch: {scene.fspyauto_last_pitch}")
            box.label(text=f"Roll:  {scene.fspyauto_last_roll}")
            box.label(text=f"Yaw:   {scene.fspyauto_last_yaw}")

        layout.separator()

        # ── Uppdatera modell ──
        layout.operator("fspyauto.update_model", icon='IMPORT')


# ─── REGISTRERING ─────────────────────────────────────────────────────────────

classes = [
    FSPYAUTO_OT_import_photo,
    FSPYAUTO_OT_update_model,
    FSPYAUTO_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.fspyauto_model_version = StringProperty(default="")
    bpy.types.Scene.fspyauto_last_fov      = StringProperty(default="")
    bpy.types.Scene.fspyauto_last_pitch    = StringProperty(default="")
    bpy.types.Scene.fspyauto_last_roll     = StringProperty(default="")
    bpy.types.Scene.fspyauto_last_yaw      = StringProperty(default="")

    # Kolla modell vid start (tyst, ingen force)
    from .downloader import ensure_model, get_local_model_version
    status, _ = ensure_model()
    if status == "ok":
        version = get_local_model_version()
        if version:
            import bpy as _bpy
            _bpy.context.scene.fspyauto_model_version = version


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.fspyauto_model_version
    del bpy.types.Scene.fspyauto_last_fov
    del bpy.types.Scene.fspyauto_last_pitch
    del bpy.types.Scene.fspyauto_last_roll
    del bpy.types.Scene.fspyauto_last_yaw


if __name__ == "__main__":
    register()
