import os
import json
import ctypes
from ui import L4D2LinkerUI
from threads import TaskWorker
import pathdisc
from manager_core import ModManagerCore

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except: return False

class AppController:
    def __init__(self):
        self.app = L4D2LinkerUI()
        self.cancel_flag = False
        self.core = None
        self.config_file = "config.json"
        
        # The Thread Lock: Prevents double-loading and disappearing UI cards
        self.is_working = False 

        # Bind UI callbacks
        self.app.on_install_clicked = self.start_install
        self.app.on_update_check_clicked = self.start_update_check
        self.app.on_refresh_clicked = self.start_audit
        self.app.on_cancel_clicked = self.request_cancel
        self.app.on_browse_clicked = self.handle_manual_path
        self.app.on_migrate_clicked = self.start_migration

        # Try to load the saved path from config.json first
        self.addons_dir = self.load_saved_path()

        # If no saved path, fallback to slow auto-detect
        if not self.addons_dir:
            self.app.append_log("[System] No saved path found. Attempting auto-detect...")
            steam_path = pathdisc.get_steam_path(self.app.append_log)
            _, self.addons_dir = pathdisc.find_l4d2_paths(steam_path, self.app.append_log) if steam_path else (None, None)

        # Boot the core system
        if self.addons_dir and os.path.exists(self.addons_dir):
            self.app.path_entry.insert(0, self.addons_dir)
            self.initialize_core(self.addons_dir)
            self.start_startup_sequence()
        else:
            self.app.append_log("[Warning] Could not locate L4D2 addons directory. Please Browse manually.")
            self.app.update_status("Waiting for Game Path")

    def load_saved_path(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f).get("addons_dir")
            except Exception: pass
        return None

    def save_path(self, path):
        with open(self.config_file, "w") as f:
            json.dump({"addons_dir": path}, f)

    def handle_manual_path(self, selected_dir):
        self.addons_dir = selected_dir
        self.save_path(selected_dir)
        self.app.append_log(f"[System] Saved new addons directory: {selected_dir}")
        self.initialize_core(self.addons_dir)
        self.start_startup_sequence()

    def initialize_core(self, addons_path):
        self.core = ModManagerCore(
            addons_dir=addons_path,
            log_callback=self.app.append_log,
            status_callback=self.app.update_status
        )

    def request_cancel(self):
        self.cancel_flag = True
        self.app.update_status("Cancelling... Please wait.")
        self.app.btn_cancel.configure(state="disabled")

    def is_cancelled(self):
        return self.cancel_flag

    def _run_in_background(self, target_workflow, status_text, *args):
        if not self.core:
            self.app.append_log("[Error] Please browse for your L4D2 addons folder first.")
            return
            
        # The Barrier: If a task is already running, reject this command to prevent UI wiping
        if self.is_working:
            return 
            
        self.is_working = True
        self.cancel_flag = False
        self.app.set_busy_state(True)
        self.app.update_status(status_text)
        
        worker = TaskWorker(
            task_function=target_workflow,
            on_finish=self._on_task_finish,
            log_callback=self.app.append_log,
            *args
        )
        worker.start()

    def _on_task_finish(self):
        self.is_working = False # Release the lock so new buttons can be clicked
        self.app.set_busy_state(False)
        if self.cancel_flag:
            self.app.update_status("Cancelled by User")
            self.app.append_log("[System] Action cancelled.")
        else:
            self.app.update_status("Ready")

    def start_startup_sequence(self):
        """The master unified boot process."""
        self._run_in_background(self._startup_workflow, "Initializing System...")

    def _startup_workflow(self, log_callback):
        success = self.core.verify_steamcmd()
        if not success:
            log_callback("[Error] Core engine halted. Missing SteamCMD.")
            return
            
        self.app.clear_mods()
        self.core.reconcile_with_disk()
        self.core.populate_ui(live_update_callback=self.app.add_single_mod, is_cancelled=self.is_cancelled)

    def start_install(self):
        raw_input = self.app.url_entry.get().strip()
        mod_id = self.core.extract_mod_id(raw_input)
        if not mod_id:
            self.app.append_log("[Error] Please enter a valid Workshop ID or URL.")
            return
        self.app.url_entry.delete(0, "end")
        self._run_in_background(self._install_workflow, f"Installing {mod_id}...", mod_id)

    def _install_workflow(self, log_callback, mod_id):
        self.core.install_mod(mod_id, live_update_callback=self.app.add_single_mod)

    def start_update_check(self):
        self._run_in_background(self._update_workflow, "Checking for updates...")

    def _update_workflow(self, log_callback):
        self.core.check_and_update_all(live_update_callback=self.app.add_single_mod, is_cancelled=self.is_cancelled)

    def start_audit(self):
        self._run_in_background(self._audit_workflow, "Auditing disk files...")

    def _audit_workflow(self, log_callback):
        self.app.clear_mods()
        self.core.reconcile_with_disk()
        self.core.populate_ui(live_update_callback=self.app.add_single_mod, is_cancelled=self.is_cancelled)

    def start_migration(self):
        self._run_in_background(self._migration_workflow, "Migrating Steam Mods...")

    def _migration_workflow(self, log_callback):
        success = self.core.migrate_workshop_folder()
        if success:
            log_callback("[System] Registering newly migrated mods...")
            self.app.clear_mods()
            self.core.reconcile_with_disk()
            self.core.populate_ui(live_update_callback=self.app.add_single_mod, is_cancelled=self.is_cancelled)

    def run(self):
        self.app.mainloop()

if __name__ == "__main__":
    controller = AppController()
    controller.run()