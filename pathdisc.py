import os
import winreg

def get_steam_path(log_callback):
    log_callback("-> Reading Windows Registry for Steam path...")
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        path, _ = winreg.QueryValueEx(registry_key, "SteamPath")
        winreg.CloseKey(registry_key)
        return os.path.normpath(path)
    except Exception as e:
        log_callback(f"[Error] Could not find Steam in Registry: {e}")
        return None

def find_l4d2_paths(steam_path, log_callback):
    log_callback("-> Scanning Steam Library Folders for L4D2...")
    
    # 1. Check the default Steam installation directory first
    default_l4d2 = os.path.join(steam_path, "steamapps", "common", "Left 4 Dead 2")
    if os.path.exists(default_l4d2):
        return _build_paths(steam_path)
        
    # 2. Parse libraryfolders.vdf if the game is on another drive
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf_path):
        with open(vdf_path, "r", encoding="utf-8") as file:
            for line in file:
                if '"path"' in line.lower():
                    parts = line.split('"')
                    if len(parts) >= 4:
                        library_path = parts[3].replace('\\\\', '\\')
                        check_path = os.path.join(library_path, "steamapps", "common", "Left 4 Dead 2")
                        if os.path.exists(check_path):
                            return _build_paths(library_path)
                            
    log_callback("[Error] Left 4 Dead 2 installation not found.")
    return None, None

def _build_paths(base_library_path):
    workshop_dir = os.path.join(base_library_path, "steamapps", "workshop", "content", "550")
    addons_dir = os.path.join(base_library_path, "steamapps", "common", "Left 4 Dead 2", "left4dead2", "addons")
    return workshop_dir, addons_dir