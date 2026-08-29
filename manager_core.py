import time
import os
import sys
import re
import json
import glob
import urllib.request
import urllib.parse
import subprocess
import shutil
import zipfile
import io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

MANIFEST_PATH = "mod_manifest.json"

# Safely determine the true location of the application
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the bulletproof path
STEAMCMD_PATH = os.path.join(APP_DIR, "steamcmd", "steamcmd.exe")


class ModManagerCore:
    def __init__(self, addons_dir, log_callback, status_callback):
        self.addons_dir = addons_dir
        self.log = log_callback
        self.set_status = status_callback
        self.image_cache_dir = os.path.join(self.addons_dir, ".image_cache")
        os.makedirs(self.image_cache_dir, exist_ok=True)
        self.manifest = self._load_manifest()

    def migrate_workshop_folder(self):
        """Universal script to migrate raw Steam files to the standalone manager."""
        workshop_dir = os.path.join(self.addons_dir, "workshop")
        
        if not os.path.exists(workshop_dir):
            self.log("[System] No workshop folder found to migrate.")
            return False

        self.set_status("Migrating old Steam mods...")
        moved_count = 0
        
        for filename in os.listdir(workshop_dir):
            if filename.endswith(".vpk") and filename[:-4].isdigit():
                mod_id = filename[:-4]
                old_path = os.path.join(workshop_dir, filename)
                new_path = os.path.join(self.addons_dir, f"workshop_{mod_id}.vpk")
                
                try:
                    shutil.move(old_path, new_path)
                    moved_count += 1
                    self.log(f"-> Migrated Mod ID: {mod_id}")
                except Exception as e:
                    self.log(f"[Error] Could not move {filename}: {e}")
                    
            elif filename.endswith(".jpg"):
                try:
                    os.remove(os.path.join(workshop_dir, filename))
                except Exception:
                    pass
        
        if moved_count > 0:
            self.log(f"[Success] Safely migrated {moved_count} mods to the root addons folder!")
            return True
        else:
            self.log("[System] Workshop folder is empty. Nothing to migrate.")
            return False

    def _load_manifest(self):
        if os.path.exists(MANIFEST_PATH):
            try:
                with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_manifest(self):
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=4)

    @staticmethod
    def extract_mod_id(input_str: str) -> str:
        input_str = input_str.strip()
        if input_str.isdigit():
            return input_str
        match = re.search(r"[?&]id=(\d+)", input_str)
        if match:
            return match.group(1)
        return ""

    def verify_steamcmd(self):
        """Checks for SteamCMD and downloads it directly from Valve if missing."""
        steamcmd_dir = os.path.dirname(STEAMCMD_PATH)
        os.makedirs(steamcmd_dir, exist_ok=True)

        if os.path.exists(STEAMCMD_PATH):
            return True

        self.set_status("First time setup: Downloading SteamCMD...")
        self.log("[System] SteamCMD not found. Downloading from Valve servers...")
        
        try:
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            response = urllib.request.urlopen(url, timeout=15)
            
            with zipfile.ZipFile(io.BytesIO(response.read())) as zip_ref:
                zip_ref.extractall(steamcmd_dir)
                
            self.log("[System] SteamCMD successfully installed!")
            return True
        except Exception as e:
            self.log(f"[Error] Failed to download SteamCMD: {e}")
            return False

    def fetch_steam_metadata(self, mod_ids):
        if not mod_ids:
            return {}
        url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
        data_dict = {"itemcount": len(mod_ids)}
        for j, wid in enumerate(mod_ids):
            data_dict[f"publishedfileids[{j}]"] = wid

        data = urllib.parse.urlencode(data_dict).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        
        results = {}
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                details = json.loads(response.read().decode("utf-8")).get("response", {}).get("publishedfiledetails", [])
                for item in details:
                    wid = str(item.get("publishedfileid"))
                    tags = [t.get("tag", "") for t in item.get("tags", [])]
                    
                    category = "Miscellaneous"
                    for tag in tags:
                        if tag in ["Campaigns", "Weapons", "Survivors", "UI / HUD", "Audio"]:
                            category = tag
                            break

                    results[wid] = {
                        "id": wid,
                        "title": item.get("title", f"Mod_{wid}"),
                        "display_title": item.get("title", f"Mod_{wid}"),
                        "time_updated": item.get("time_updated", 0),
                        "preview_url": item.get("preview_url", ""),
                        "description": item.get("description", "No description provided."),
                        "category": category
                    }
        except Exception as e:
            self.log(f"[Error] Failed to fetch metadata from Steam: {e}")
        return results

    def _download_single_thumbnail(self, mod_id, preview_url):
        """Worker function for downloading a single thumbnail."""
        if not preview_url:
            return
        mod_cache_dir = os.path.join(self.image_cache_dir, str(mod_id))
        os.makedirs(mod_cache_dir, exist_ok=True)
        img_path = os.path.join(mod_cache_dir, "thumb.jpg")

        if not os.path.exists(img_path):
            try:
                urllib.request.urlretrieve(preview_url, img_path)
            except Exception:
                pass

    def batch_download_thumbnails(self, mod_items):
        """Downloads all missing thumbnails concurrently across 10 worker threads."""
        missing = []
        for wid, info in mod_items:
            img_path = os.path.join(self.image_cache_dir, str(wid), "thumb.jpg")
            if not os.path.exists(img_path) and info.get("preview_url"):
                missing.append((wid, info["preview_url"]))

        if not missing:
            return

        self.set_status(f"Downloading {len(missing)} thumbnails in parallel...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._download_single_thumbnail, wid, url) for wid, url in missing]
            for _ in as_completed(futures):
                pass

    def _load_preprocessed_image(self, mod_id):
        """Loads and pre-resizes thumbnail in RAM so the GUI thread doesn't lag."""
        img_path = os.path.join(self.image_cache_dir, str(mod_id), "thumb.jpg")
        if os.path.exists(img_path):
            try:
                with Image.open(img_path) as img:
                    # .thumbnail() operates in-place instantly with minimal CPU overhead
                    rgb_img = img.convert("RGB")
                    rgb_img.thumbnail((284, 160)) 
                    return [rgb_img]
            except Exception:
                pass
        return []

    def download_via_steamcmd(self, mod_id):
        if not os.path.exists(STEAMCMD_PATH):
            raise FileNotFoundError(f"SteamCMD not found at {STEAMCMD_PATH}. Place steamcmd.exe in the 'steamcmd' directory.")

        self.log(f"-> Launching SteamCMD download for Mod ID: {mod_id}...")
        command = [
            STEAMCMD_PATH,
            "+login", "anonymous",
            "+workshop_download_item", "550", str(mod_id),
            "+quit"
        ]

        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run(command, check=True, creationflags=flags)

        base_dir = os.path.dirname(STEAMCMD_PATH)
        download_dir = os.path.join(base_dir, "steamapps", "workshop", "content", "550", str(mod_id))
        
        vpk_files = glob.glob(os.path.join(download_dir, "*.vpk"))
        if not vpk_files:
            raise FileNotFoundError("SteamCMD finished, but no .vpk file was extracted.")
            
        return vpk_files[0], download_dir

    def install_mod(self, mod_id, live_update_callback=None):
        meta_dict = self.fetch_steam_metadata([mod_id])
        meta = meta_dict.get(str(mod_id))
        if not meta:
            self.log(f"[Error] Could not find Mod ID {mod_id} on Steam Workshop.")
            return False

        safe_title = "".join(c for c in meta['title'] if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
        target_vpk_name = f"workshop_{mod_id}_{safe_title}.vpk"
        target_vpk_path = os.path.join(self.addons_dir, target_vpk_name)

        self.set_status(f"Downloading: {meta['title']}...")
        try:
            downloaded_vpk, download_dir = self.download_via_steamcmd(mod_id)
            
            if os.path.exists(target_vpk_path):
                os.remove(target_vpk_path)
            shutil.move(downloaded_vpk, target_vpk_path)
            
            shutil.rmtree(download_dir, ignore_errors=True)

            self._download_single_thumbnail(mod_id, meta.get("preview_url"))
            images = self._load_preprocessed_image(mod_id)

            self.manifest[str(mod_id)] = {
                "id": str(mod_id),
                "title": meta['title'],
                "safe_title": safe_title,
                "category": meta['category'],
                "description": meta['description'],
                "time_updated": meta['time_updated'],
                "file_name": target_vpk_name,
                "preview_url": meta.get("preview_url", "")
            }
            self._save_manifest()
            
            self.log(f"[Success] Installed: {meta['title']}")
            
            if live_update_callback:
                ui_data = {**self.manifest[str(mod_id)], "loaded_images": images}
                live_update_callback(ui_data)
            return True
        except Exception as e:
            self.log(f"[Error] Failed installing {mod_id}: {e}")
            return False

    def reconcile_with_disk(self):
        self.set_status("Reconciling disk files with manifest...")
        if not os.path.exists(self.addons_dir):
            return
            
        disk_files = os.listdir(self.addons_dir)
        modified = False

        for mod_id in list(self.manifest.keys()):
            file_name = self.manifest[mod_id].get("file_name", "")
            file_path = os.path.join(self.addons_dir, file_name)
            if not os.path.exists(file_path):
                self.log(f"[-] Detected manual deletion: {self.manifest[mod_id].get('title')} ({mod_id})")
                cache_folder = os.path.join(self.image_cache_dir, str(mod_id))
                if os.path.exists(cache_folder):
                    shutil.rmtree(cache_folder, ignore_errors=True)
                del self.manifest[mod_id]
                modified = True

        untracked = []
        for f in disk_files:
            if f.startswith("workshop_") and f.endswith(".vpk"):
                clean_name = f.replace(".vpk", "")
                parts = clean_name.split("_")
                
                if len(parts) >= 2 and parts[1].isdigit():
                    wid = parts[1]
                    if wid not in self.manifest:
                        untracked.append((wid, f))

        if untracked:
            ids_to_fetch = [u[0] for u in untracked]
            meta_dict = self.fetch_steam_metadata(ids_to_fetch)
            for wid, f_name in untracked:
                meta = meta_dict.get(wid, {"title": f"Mod_{wid}", "time_updated": 0, "category": "Miscellaneous", "description": ""})
                safe_title = "".join(c for c in meta['title'] if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
                self.manifest[wid] = {
                    "id": wid,
                    "title": meta['title'],
                    "safe_title": safe_title,
                    "category": meta.get("category", "Miscellaneous"),
                    "description": meta.get("description", ""),
                    "time_updated": meta['time_updated'],
                    "file_name": f_name,
                    "preview_url": meta.get("preview_url", "")
                }
                modified = True
                self.log(f"[+] Adopted existing addon: {meta['title']}")

        if modified:
            self._save_manifest()

    def populate_ui(self, live_update_callback, is_cancelled):
        if not self.manifest:
            return

        # Parallelize network downloads first
        self.batch_download_thumbnails(list(self.manifest.items()))

        # Sort alphabetically in RAM
        sorted_mods = sorted(self.manifest.items(), key=lambda item: item[1].get("title", "").lower())
        
        self.set_status("Rendering mod cards...")
        for mod_id, info in sorted_mods:
            if is_cancelled():
                break
            images = self._load_preprocessed_image(mod_id)
            card_data = {**info, "display_title": info.get("title", f"Mod {mod_id}"), "loaded_images": images}
            live_update_callback(card_data)

            time.sleep(0.09)

    def check_and_update_all(self, live_update_callback, is_cancelled):
        if not self.manifest:
            self.set_status("Ready (No mods installed)")
            return

        self.set_status("Checking for workshop updates...")
        mod_ids = list(self.manifest.keys())
        remote_metadata = self.fetch_steam_metadata(mod_ids)
        
        updates_needed = []
        for wid, local_data in self.manifest.items():
            remote = remote_metadata.get(wid)
            if remote and remote["time_updated"] > local_data.get("time_updated", 0):
                updates_needed.append(wid)

        if not updates_needed:
            self.log("[System] All mods are up to date.")
            self.set_status("Ready")
            return

        self.log(f"-> Found {len(updates_needed)} updates. Downloading...")
        for i, wid in enumerate(updates_needed):
            if is_cancelled():
                self.log("[System] Update process halted by user.")
                break
            self.set_status(f"Updating ({i+1}/{len(updates_needed)})...")
            self.install_mod(wid, live_update_callback)

        self.set_status("Ready")