import os
import sys
import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image

def resource_path(relative_path):
    """Gets the absolute path to a bundled resource for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores its path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ModCard(ctk.CTkFrame):
    def __init__(self, master, mod_data):
        super().__init__(master, corner_radius=10, fg_color=("#e0e0e6", "#2b2b36"))
        self.mod_data = mod_data
        self.is_expanded = False
        self.images = []
        self.current_img_idx = 0
        self.on_refresh_clicked = None
        self.on_cancel_clicked = None
        self.on_browse_clicked = None
        self.on_migrate_clicked = None
        self.pack(fill="x", padx=10, pady=6, expand=True)
        self._load_images()
        self._build_card()

    def _load_images(self):
        ram_images = self.mod_data.get("loaded_images", [])
        for pil_img in ram_images:
            try:
                thumbnail = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(284, 160))
                self.images.append(thumbnail)
            except Exception as e:
                print(f"[UI Debug] Render error: {e}")

    def _build_card(self):
        self.main_row = ctk.CTkFrame(self, fg_color="transparent")
        self.main_row.pack(fill="x", padx=10, pady=10)

        self.carousel_frame = ctk.CTkFrame(self.main_row, fg_color="transparent", width=284)
        self.carousel_frame.pack(side="left", padx=(0, 15))

        self.img_label = ctk.CTkLabel(self.carousel_frame, text="[No Image]", width=284, height=160, fg_color="#1a1a24")
        self.img_label.pack(side="top")

        if len(self.images) > 0:
            self.img_label.configure(text="", image=self.images[0])

        if len(self.images) > 1:
            self.nav_frame = ctk.CTkFrame(self.carousel_frame, fg_color="transparent")
            self.nav_frame.pack(side="top", fill="x", pady=(5, 0))
            
            self.btn_prev = ctk.CTkButton(self.nav_frame, text="<", width=30, height=22, command=self._prev_img)
            self.btn_prev.pack(side="left", padx=2)
            
            self.lbl_counter = ctk.CTkLabel(self.nav_frame, text=f"1 / {len(self.images)}", font=("Segoe UI", 11, "bold"))
            self.lbl_counter.pack(side="left", expand=True)
            
            self.btn_next = ctk.CTkButton(self.nav_frame, text=">", width=30, height=22, command=self._next_img)
            self.btn_next.pack(side="right", padx=2)

        self.info_frame = ctk.CTkFrame(self.main_row, fg_color="transparent")
        self.info_frame.pack(side="left", fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            self.info_frame, 
            text=self.mod_data.get("display_title", "Unknown Mod"), 
            font=("Segoe UI", 16, "bold"), 
            anchor="w", 
            wraplength=450
        )
        self.title_label.pack(fill="x", anchor="w")

        self.meta_label = ctk.CTkLabel(
            self.info_frame, 
            text=f"Category: {self.mod_data.get('category', 'Miscellaneous')}  |  ID: {self.mod_data.get('id')}", 
            font=("Segoe UI", 12), 
            text_color="gray", 
            anchor="w"
        )
        self.meta_label.pack(fill="x", pady=(2, 10))

        self.btn_toggle = ctk.CTkButton(self.info_frame, text="▼ Show Description", width=120, height=28, command=self.toggle_description)
        self.btn_toggle.pack(anchor="w")

        self.desc_frame = ctk.CTkFrame(self, fg_color=("#d0d0d8", "#202028"), corner_radius=6)
        self.desc_text = ctk.CTkLabel(
            self.desc_frame, 
            text=self.mod_data.get("description", "No description provided.").replace("<br>", "\n"), 
            wraplength=700, 
            justify="left", 
            font=("Segoe UI", 12)
        )
        self.desc_text.pack(padx=15, pady=10, fill="x")

    def _prev_img(self):
        if self.images:
            self.current_img_idx = (self.current_img_idx - 1) % len(self.images)
            self.img_label.configure(image=self.images[self.current_img_idx])
            self.lbl_counter.configure(text=f"{self.current_img_idx + 1} / {len(self.images)}")

    def _next_img(self):
        if self.images:
            self.current_img_idx = (self.current_img_idx + 1) % len(self.images)
            self.img_label.configure(image=self.images[self.current_img_idx])
            self.lbl_counter.configure(text=f"{self.current_img_idx + 1} / {len(self.images)}")

    def toggle_description(self):
        if self.is_expanded:
            self.desc_frame.pack_forget()
            self.btn_toggle.configure(text="▼ Show Description")
            self.is_expanded = False
        else:
            self.desc_frame.pack(fill="x", padx=10, pady=(0, 10))
            self.btn_toggle.configure(text="▲ Hide Description")
            self.is_expanded = True


class L4D2LinkerUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("L4D2 Workshop Mod Manager")
        self.geometry("950x780")
        self.minsize(850, 600)
        self.resizable(True, True) 
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.on_install_clicked = None
        self.on_update_check_clicked = None
        self.on_refresh_clicked = None
        self.on_cancel_clicked = None
        
        self.categories = ["All", "Campaigns", "Weapons", "Survivors", "UI / HUD", "Audio", "Miscellaneous"]
        self.all_mod_cards = []
        self._build_interface()

    def _build_interface(self):
        # 1. Top Control Bar
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(pady=10, padx=15, fill="x")

        self.status_label = ctk.CTkLabel(self.top_frame, text="Status: Ready", font=("Segoe UI", 14, "bold"))
        self.status_label.pack(side="left", padx=15, pady=10)

        self.btn_cancel = ctk.CTkButton(self.top_frame, text="Stop", fg_color="#FF8C00", hover_color="#B86500", command=self._trigger_cancel, state="disabled", width=70)
        self.btn_cancel.pack(side="right", padx=5, pady=10)

        self.btn_refresh = ctk.CTkButton(self.top_frame, text="Audit Disk", width=90, command=self._trigger_refresh)
        self.btn_refresh.pack(side="right", padx=5, pady=10)

        self.btn_migrate = ctk.CTkButton(
            self.top_frame, 
            text="Migrate Steam Mods", 
            width=130, 
            fg_color="#4B0082", 
            hover_color="#300055", 
            command=self._trigger_migrate
        )
        self.btn_migrate.pack(side="right", padx=5, pady=10)

        self.btn_update = ctk.CTkButton(self.top_frame, text="Check Updates", width=110, command=self._trigger_update_check)
        self.btn_update.pack(side="right", padx=5, pady=10)

        #Manual path override for workshop directory
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.pack(pady=(0, 5), padx=15, fill="x")

        self.path_entry = ctk.CTkEntry(self.path_frame, placeholder_text="Manual Addons Folder Path (e.g., C:/Steam/steamapps/common/Left 4 Dead 2/left4dead2/addons)...")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse = ctk.CTkButton(self.path_frame, text="Browse", width=80, command=self._trigger_browse)
        self.btn_browse.pack(side="right")

        # 2. Mod Downloader Bar
        self.add_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.add_frame.pack(pady=(0, 5), padx=15, fill="x")

        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(pady=(0, 5), padx=15, fill="x")

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search mods by name...")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._filter_mods) # Triggers on every keystroke

        self.url_entry = ctk.CTkEntry(self.add_frame, placeholder_text="Paste Steam Workshop URL or ID to install...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_install = ctk.CTkButton(self.add_frame, text="Install Mod", fg_color="#228B22", hover_color="#006400", width=100, command=self._trigger_install)
        self.btn_install.pack(side="right")

        # 3. Categorized Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(pady=10, padx=15, fill="both", expand=True)

        self.scroll_frames = {}
        for cat in self.categories:
            self.tabview.add(cat)
            scroll = ctk.CTkScrollableFrame(self.tabview.tab(cat))
            scroll.pack(fill="both", expand=True)
            self.scroll_frames[cat] = scroll

        # 4. Logs & Copyright
        self.log_box = ctk.CTkTextbox(self, height=90, state="disabled", font=("Consolas", 11))
        self.log_box.pack(pady=(0, 5), padx=15, fill="x")

        self.footer_label = ctk.CTkLabel(
            self, 
            text="© 2026 Percival Valencia. All rights reserved.", 
            font=("Segoe UI", 10), 
            text_color="gray"
        )
        self.footer_label.pack(side="bottom", pady=(0, 4))

    def clear_mods(self):
        """Safely destroys all tracked mod cards and sweeps the GUI frames."""
        def _clear():
            # 1. Clear the master memory list
            for card in self.all_mod_cards:
                try: card.destroy()
                except: pass
            self.all_mod_cards.clear()
            
            # 2. Hard-sweep the visual frames for any orphaned UI elements
            for frame in self.scroll_frames.values():
                for widget in frame.winfo_children():
                    try: widget.destroy()
                    except: pass
                    
        self.after(0, _clear)

    def add_single_mod(self, mod):
        """Instantiates cards, sorts the master list, and triggers the filter."""
        def _add():
            cat = mod.get("category", "Miscellaneous")
            
            # Create and track the category-specific card
            if cat in self.scroll_frames:
                card_cat = ModCard(self.scroll_frames[cat], mod)
                self.all_mod_cards.append(card_cat)
            
            # Create and track the universal 'All' card
            card_all = ModCard(self.scroll_frames["All"], mod)
            self.all_mod_cards.append(card_all)
            
            # Keep the master memory list strictly alphabetical
            self.all_mod_cards.sort(key=lambda c: c.mod_data.get("display_title", "").lower())
            
            # Re-pack the UI dynamically
            self._filter_mods()
        self.after(0, _add)

    def _filter_mods(self, event=None):
        """Unpacks all cards and repacks only the ones matching the search query."""
        query = self.search_entry.get().lower()
        
        # 1. Unpack everything to reset Tkinter's stacking order
        for card in self.all_mod_cards:
            card.pack_forget()
            
        # 2. Repack matching cards in their perfect alphabetical order
        for card in self.all_mod_cards:
            title = card.mod_data.get("display_title", "").lower()
            if query in title:
                card.pack(fill="x", padx=10, pady=6, expand=True)

    def _trigger_install(self):
        if self.on_install_clicked: self.on_install_clicked()

    def _trigger_update_check(self):
        if self.on_update_check_clicked: self.on_update_check_clicked()

    def _trigger_refresh(self):
        if self.on_refresh_clicked: self.on_refresh_clicked()

    def _trigger_cancel(self):
        if self.on_cancel_clicked: self.on_cancel_clicked()

    def _trigger_migrate(self):
        if self.on_migrate_clicked: 
            self.on_migrate_clicked()

    def _trigger_browse(self):
        selected_dir = filedialog.askdirectory(title="Select L4D2 addons folder")
        if selected_dir:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, selected_dir)
            if self.on_browse_clicked: 
                self.on_browse_clicked(selected_dir)

    def update_status(self, text: str):
        self.after(0, lambda: self.status_label.configure(text=f"Status: {text}"))

    def set_busy_state(self, is_busy: bool):
        state = "disabled" if is_busy else "normal"
        cancel_state = "normal" if is_busy else "disabled"
        
        self.after(0, lambda: self.btn_install.configure(state=state))
        self.after(0, lambda: self.btn_update.configure(state=state))
        self.after(0, lambda: self.btn_refresh.configure(state=state))
        self.after(0, lambda: self.btn_cancel.configure(state=cancel_state))

    def append_log(self, message: str):
        def _update():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{message}\n")
            self.log_box.configure(state="disabled")
            self.log_box.see("end")
        self.after(0, _update)

    

if __name__ == "__main__":
    app = L4D2LinkerUI()
    app.mainloop()