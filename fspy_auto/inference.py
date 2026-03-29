import os
import math
import sys


def _ensure_torch():
    """Försök importera torch - ge tydligt felmeddelande om det saknas."""
    try:
        import torch
        return torch
    except ImportError:
        raise ImportError(
            "PyTorch är inte installerat i Blenders Python-miljö.\n"
            "Öppna Blenders Python-konsol och kör:\n"
            "  import pip; pip.main(['install', 'torch', 'torchvision'])"
        )


def run_inference(image_path):
    """
    Kör inferens på en bild och returnerar en dict med kameraparametrar.
    """
    torch = _ensure_torch()
    import torch.nn as nn
    from torchvision import transforms, models
    from PIL import Image
    from .downloader import get_model_path

    model_path = get_model_path()
    if not os.path.exists(model_path):
        raise FileNotFoundError("Modellen är inte nedladdad ännu. Tryck på 'Uppdatera modell' först.")

    # Välj device
    if torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    # Bygg modell (samma arkitektur som train.py)
    class FSpyNet(nn.Module):
        def __init__(self):
            super().__init__()
            backbone = models.resnet18(weights=None)
            self.features = nn.Sequential(*list(backbone.children())[:-1])
            self.regressor = nn.Sequential(
                nn.Flatten(),
                nn.Linear(512, 256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, 4)
            )

        def forward(self, x):
            x = self.features(x)
            return self.regressor(x)

    model = FSpyNet().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])

    img = Image.open(image_path).convert("RGB")
    tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        pred = model(tensor)[0].cpu().tolist()

    fov, pitch, roll, yaw = pred
    sensor_width = 36.0
    focal_length = sensor_width / (2 * math.tan(math.radians(fov / 2)))

    return {
        "image_path":    os.path.abspath(image_path),
        "fov_degrees":   fov,
        "focal_length_mm": focal_length,
        "sensor_width_mm": sensor_width,
        "pitch_degrees": pitch,
        "roll_degrees":  roll,
        "yaw_degrees":   yaw,
    }


def apply_to_blender(result):
    """Applicerar kameraparametrar på aktiv kamera i Blender."""
    import bpy

    scene = bpy.context.scene
    cam_obj = scene.camera

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
