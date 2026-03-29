import os
import json
import urllib.request

GITHUB_REPO = "davidbicho/fspy-auto"  # Ändra till ditt repo
GITHUB_API  = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
MODEL_FILENAME = "best_model.pt"
VERSION_FILENAME = "model_version.txt"


def get_addon_dir():
    import bpy
    return os.path.dirname(os.path.abspath(__file__))


def get_model_path():
    return os.path.join(get_addon_dir(), MODEL_FILENAME)


def get_version_path():
    return os.path.join(get_addon_dir(), VERSION_FILENAME)


def get_local_model_version():
    path = get_version_path()
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return None


def get_latest_release_info():
    try:
        req = urllib.request.Request(
            GITHUB_API,
            headers={"User-Agent": "fspy-auto-blender-addon"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        tag = data["tag_name"]
        model_url = None
        for asset in data["assets"]:
            if asset["name"] == MODEL_FILENAME:
                model_url = asset["browser_download_url"]
                break

        return tag, model_url
    except Exception as e:
        print(f"[fspy-auto] Kunde inte nå GitHub: {e}")
        return None, None


def download_model(url, progress_callback=None):
    path = get_model_path()
    tmp_path = path + ".tmp"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fspy-auto-blender-addon"})
        with urllib.request.urlopen(req) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536

            with open(tmp_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded / total)

        os.replace(tmp_path, path)
        return True
    except Exception as e:
        print(f"[fspy-auto] Nedladdning misslyckades: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


def ensure_model(force=False):
    """
    Kollar om modellen är uppdaterad och laddar ner om det behövs.
    Returnerar (status, message) där status är 'ok', 'downloading', eller 'error'.
    """
    model_path = get_model_path()
    local_version = get_local_model_version()

    # Kolla senaste versionen på GitHub
    latest_version, model_url = get_latest_release_info()

    if latest_version is None:
        # Ingen internetåtkomst - använd lokal modell om den finns
        if os.path.exists(model_path):
            return "ok", f"Offline - använder lokal modell ({local_version or 'okänd version'})"
        else:
            return "error", "Ingen modell hittad och ingen internetåtkomst"

    if not force and local_version == latest_version and os.path.exists(model_path):
        return "ok", f"Modell är uppdaterad ({latest_version})"

    # Ladda ner
    print(f"[fspy-auto] Laddar ner modell {latest_version}...")
    success = download_model(model_url)

    if success:
        with open(get_version_path(), "w") as f:
            f.write(latest_version)
        return "ok", f"Modell nedladdad ({latest_version})"
    else:
        return "error", "Nedladdning misslyckades"
