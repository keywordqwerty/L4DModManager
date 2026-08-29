import os
import shutil

# Using the exact path from your screenshot
addons_dir = r"D:\Games\Left 4 Dead 2\left4dead2\addons\workshop"
workshop_dir = os.path.join(addons_dir, "workshop")

if not os.path.exists(workshop_dir):
    print("Workshop folder not found. Check your path.")
    exit()

moved_count = 0
for filename in os.listdir(workshop_dir):
    # 1. Move and rename the .vpk files
    if filename.endswith(".vpk") and filename[:-4].isdigit():
        mod_id = filename[:-4]
        old_path = os.path.join(workshop_dir, filename)
        new_path = os.path.join(addons_dir, f"workshop_{mod_id}.vpk")
        
        shutil.move(old_path, new_path)
        moved_count += 1
        print(f"Migrated Mod ID: {mod_id}")
        
    # 2. Delete the old Steam .jpg files (your manager handles its own high-res cache now)
    elif filename.endswith(".jpg"):
        os.remove(os.path.join(workshop_dir, filename))

print(f"\nMigration complete! Successfully moved {moved_count} mods.")
print("You can now open your Mod Manager and click 'Audit Disk'.")