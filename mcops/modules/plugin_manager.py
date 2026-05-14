import os
import shutil
from pathlib import Path
from mcops.config import PLUGIN_POOL_DIR, INSTANCES_DIR

def list_pool_plugins() -> list[dict]:
    """Returns a list of all plugins in the global pool."""
    plugins = []
    if not PLUGIN_POOL_DIR.exists():
        return plugins
    for file in PLUGIN_POOL_DIR.iterdir():
        if file.is_file() and file.suffix == '.jar':
            stat = file.stat()
            plugins.append({
                "filename": file.name,
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime
            })
    return plugins

def find_plugin_in_pool(plugin_name: str) -> Path | None:
    """Fuzzy matches a plugin name against the pool.
    e.g. 'LuckPerms' -> 'LuckPerms-5.4.102.jar'
    """
    for file in PLUGIN_POOL_DIR.iterdir():
        if file.is_file() and file.suffix == '.jar':
            if file.name.lower().startswith(plugin_name.lower()):
                return file
    return None

def copy_plugin_to_instance(plugin_name: str, server_name: str, is_mod: bool = False) -> bool:
    """Copies a plugin from the pool to the instance's plugin/mods folder."""
    pool_plugin_path = find_plugin_in_pool(plugin_name)
    if not pool_plugin_path:
        return False
        
    folder_name = "mods" if is_mod else "plugins"
    instance_plugin_dir = INSTANCES_DIR / server_name / folder_name
    instance_plugin_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = instance_plugin_dir / pool_plugin_path.name
    shutil.copy2(pool_plugin_path, dest_path)
    return True

def save_uploaded_plugin(filename: str, content: bytes) -> Path:
    """Saves an uploaded plugin to the pool."""
    dest = PLUGIN_POOL_DIR / filename
    with open(dest, "wb") as f:
        f.write(content)
    return dest

def delete_pool_plugin(filename: str) -> bool:
    """Deletes a plugin from the pool."""
    target = PLUGIN_POOL_DIR / filename
    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False
