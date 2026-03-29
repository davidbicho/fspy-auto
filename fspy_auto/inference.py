import os
import math
import json
import urllib.request

API_URL = "http://davidbicho.com:8765/fspy-auto/predict"


def run_inference(image_path):
    """Skickar bilden till servern och returnerar kameraparametrar."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    filename = os.path.basename(image_path)
    boundary = "----fspyautoboundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Kunde inte nå fSpy Auto-servern.\n"
            f"Kontrollera internetanslutningen.\n"
            f"Fel: {e}"
        )

    result["image_path"] = os.path.abspath(image_path)
    return result


def apply_to_blender(result):
    """Applicerar kameraparametrar på aktiv kamera i Blender."""
    import bpy

    cam_obj = bpy.context.scene.camera
    if cam_obj is None:
        raise RuntimeError("Ingen kamera i scenen. Lägg till en kamera först.")

    cam = cam_obj.data

    # FOV
    cam.lens_unit = 'FOV'
    cam.angle = math.radians(result["fov_degrees"])

    # Rotation
    cam_obj.rotation_euler = (
        math.radians(result["pitch_degrees"]),
        math.radians(result["roll_degrees"]),
        math.radians(result["yaw_degrees"]),
    )

    # Bakgrundsbild
    img_path = result["image_path"]
    if os.path.exists(img_path):
        cam.show_background_images = True
        cam.background_images.clear()
        bg = cam.background_images.new()
        bg.image = bpy.data.images.load(img_path, check_existing=True)
        bg.alpha = 0.5
