# L4D2 Workshop Mod Manager

A standalone, custom Mod Manager for Left 4 Dead 2 that allows you to install, manage, and update Steam Workshop mods without relying on the Steam client's built-in workshop subscription system.

## Features

* **Direct Steam Workshop Downloads:** Downloads `.vpk` files directly from the Steam Workshop via `SteamCMD`.
* **Human-Readable File Names:** Automatically renames raw, numbered Steam `.vpk` files (e.g., `123456789.vpk`) into descriptive names (e.g., `workshop_123456789_Mod_Name.vpk`) for easy manual management.
* **Modern Categorized UI:** A sleek, CustomTkinter-based interface that categorizes your mods (Campaigns, Weapons, Survivors, UI/HUD, Audio) just like the Steam Workshop.
* **Metadata & Thumbnails:** Automatically fetches mod titles, descriptions, categories, and caches preview images to display in an image carousel within the app.
* **One-Click Updates:** Checks all managed mods against the Steam API to detect and download updates.
* **Smart Path Discovery:** Automatically locates your Left 4 Dead 2 installation via the Windows Registry and Steam library folders.
* **Seamless Migration:** Built-in tool to easily migrate your existing Steam Workshop mods over to this standalone manager.

## How It Works

The manager uses the official `SteamCMD` tool to communicate with Steam's servers and download workshop content anonymously. It parses the Steam Web API to grab the correct metadata and thumbnails for each mod, generating a local `mod_manifest.json` file to track installed mods, categories, and update timestamps.

## Prerequisites

* **Python 3.x**
* **CustomTkinter** (`pip install customtkinter`)
* **Pillow** (`pip install Pillow`)

*(Note: The app will automatically download `SteamCMD` directly from Valve's servers on first launch if it's not present.)*

## Usage

1. **Launch the Manager:** Run `python main.py`.
2. **First Time Setup:** The app will attempt to auto-detect your L4D2 `addons` folder. If it fails, you can manually browse and select it. SteamCMD will be downloaded automatically if missing.
3. **Install Mods:** Paste a Steam Workshop URL or Mod ID into the input field and click **Install Mod**.
4. **Migrate Existing Mods:** If you have mods already subscribed to via Steam, click **Migrate Steam Mods** to convert them to the manager's format.
5. **Update Mods:** Click **Check Updates** to query Steam for any newer versions of your installed mods.

## Project Structure

* `main.py` - The entry point and application controller.
* `manager_core.py` - Handles SteamCMD execution, Steam API requests, file management, and updates.
* `ui.py` - Contains the CustomTkinter GUI implementation and Mod Cards.
* `pathdisc.py` - Utilities for auto-discovering the L4D2 installation path via the Windows Registry.
* `migrate.py` - A standalone script (also integrated into the main app) for migrating existing workshop files.

## License

© 2026 Percival Valencia. All rights reserved.
