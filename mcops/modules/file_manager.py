import os
import shutil
from pathlib import Path
from mcops.config import INSTANCES_DIR

def safe_path(base_dir: str, requested_path: str) -> Path:
    """
    Löst den Pfad auf und prüft ob er innerhalb von base_dir liegt.
    Wirft ValueError wenn Path Traversal erkannt wird.
    """
    base = Path(base_dir).resolve()
    target = (base / requested_path.lstrip('/')).resolve()
    
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path traversal attempt detected: {requested_path}")
    return target

def list_directory(server_name: str, path: str) -> list[dict]:
    """Gibt Ordnerinhalt zurück: Dateien mit Größe, Änderungsdatum, Typ"""
    instance_dir = INSTANCES_DIR / server_name
    if not instance_dir.exists():
        raise FileNotFoundError("Server directory not found")
        
    target_dir = safe_path(str(instance_dir), path)
    if not target_dir.is_dir():
        raise NotADirectoryError("Path is not a directory")
        
    items = []
    for item in target_dir.iterdir():
        stat = item.stat()
        items.append({
            "name": item.name,
            "is_dir": item.is_dir(),
            "size": stat.st_size,
            "modified": stat.st_mtime
        })
    return items

def read_file(server_name: str, path: str) -> str:
    """Liest Dateiinhalt als String, max. 2MB"""
    instance_dir = INSTANCES_DIR / server_name
    target_file = safe_path(str(instance_dir), path)
    
    if not target_file.is_file():
        raise FileNotFoundError("File not found")
        
    if target_file.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("File too large to read in browser (>2MB)")
        
    with open(target_file, "r", encoding="utf-8") as f:
        return f.read()

def write_file(server_name: str, path: str, content: str) -> bool:
    """Schreibt neuen Inhalt in Datei, erstellt Backup der alten Version"""
    instance_dir = INSTANCES_DIR / server_name
    target_file = safe_path(str(instance_dir), path)
    
    if target_file.exists():
        backup_file = target_file.with_name(target_file.name + ".backup")
        shutil.copy2(target_file, backup_file)
        
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    return True

def upload_file(server_name: str, target_path: str, file_data: bytes, filename: str) -> bool:
    """Speichert hochgeladene Datei nach Whitelist-Prüfung"""
    whitelist = ['.jar', '.yml', '.toml', '.json', '.properties', '.txt', '.log']
    if not any(filename.lower().endswith(ext) for ext in whitelist):
        raise ValueError(f"File type not allowed for {filename}")
        
    instance_dir = INSTANCES_DIR / server_name
    target_dir = safe_path(str(instance_dir), target_path)
    
    if not target_dir.is_dir():
        raise NotADirectoryError("Target is not a directory")
        
    dest_file = target_dir / filename
    with open(dest_file, "wb") as f:
        f.write(file_data)
    return True

def delete_path(server_name: str, path: str) -> bool:
    """Löscht Datei oder Ordner nach Sicherheitsprüfung"""
    instance_dir = INSTANCES_DIR / server_name
    target = safe_path(str(instance_dir), path)
    
    if target == instance_dir.resolve():
        raise ValueError("Cannot delete root instance directory")
        
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return True

def rename_path(server_name: str, old_path: str, new_name: str) -> bool:
    """Benennt Datei oder Ordner um"""
    if "/" in new_name or "\\" in new_name:
        raise ValueError("New name must not contain path separators")
        
    instance_dir = INSTANCES_DIR / server_name
    source = safe_path(str(instance_dir), old_path)
    dest = source.parent / new_name
    
    safe_path(str(instance_dir), str(dest.relative_to(instance_dir)))
    
    source.rename(dest)
    return True
