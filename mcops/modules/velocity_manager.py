import os
import sys
import shutil
import time
from pathlib import Path

# libtmux is Linux-only – import conditionally
if sys.platform != "win32":
    try:
        import libtmux as _libtmux  # pyrefly: ignore[missing-import]
        _LIBTMUX_AVAILABLE = True
    except ImportError:
        _LIBTMUX_AVAILABLE = False
else:
    _LIBTMUX_AVAILABLE = False

from mcops.config import INSTANCES_DIR


def _get_tmux_server():
    """Returns a libtmux.Server instance or None if unavailable."""
    if _LIBTMUX_AVAILABLE:
        import libtmux
        return libtmux.Server()
    return None


def _get_velocity_instance_dir() -> Path | None:
    """Finds the Velocity proxy instance directory. Assumes one exists."""
    if not INSTANCES_DIR.exists():
        return None
    for instance_dir in INSTANCES_DIR.iterdir():
        if instance_dir.is_dir():
            velocity_toml = instance_dir / "velocity.toml"
            if velocity_toml.exists():
                return instance_dir
    return None


def register_server_in_velocity(server_name: str, host: str, port: int) -> bool:
    """
    Trägt einen neuen Server in velocity.toml ein.
    Gibt True zurück bei Erfolg, False bei Fehler.
    Erstellt automatisch ein Backup der velocity.toml vor der Änderung.
    """
    velocity_dir = _get_velocity_instance_dir()
    if not velocity_dir:
        return False

    toml_path = velocity_dir / "velocity.toml"
    backup_path = velocity_dir / "velocity.toml.backup"

    # Backup
    shutil.copy2(toml_path, backup_path)

    try:
        with open(toml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        out_lines = []
        in_servers_block = False
        inserted = False
        new_entry = f'{server_name.lower()} = "{host}:{port}"\n'

        for line in lines:
            if line.strip() == "[servers]":
                in_servers_block = True
                out_lines.append(line)
                continue

            if in_servers_block and line.strip().startswith("["):
                # Transitioning to next block – insert before it
                if not inserted:
                    out_lines.append(new_entry)
                    inserted = True
                in_servers_block = False

            if in_servers_block and line.strip() and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                if key.lower() == server_name.lower():
                    # Overwrite existing entry
                    out_lines.append(new_entry)
                    inserted = True
                    continue

            out_lines.append(line)

        if in_servers_block and not inserted:
            out_lines.append(new_entry)

        with open(toml_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)

        return True
    except Exception as e:
        shutil.copy2(backup_path, toml_path)
        print(f"Error modifying velocity.toml: {e}")
        return False


def reload_velocity_proxy() -> bool:
    """
    Sendet 'velocity reload' an die tmux-Session des Proxy-Servers.
    Gibt True zurück wenn Reload erfolgreich, False bei Timeout.
    """
    velocity_dir = _get_velocity_instance_dir()
    if not velocity_dir:
        return False

    server = _get_tmux_server()
    if not server:
        return False

    session_name = f"mc_{velocity_dir.name}"
    try:
        session = server.sessions.get(session_name=session_name)
    except Exception:
        session = None

    if not session:
        return False

    window = session.attached_window
    pane = window.attached_pane
    pane.send_keys("velocity reload")

    timeout = 5
    start_time = time.time()
    while time.time() - start_time < timeout:
        output = pane.cmd("capture-pane", "-p").stdout
        output_str = "\n".join(output)
        if "Done reloading" in output_str or "Reloaded configuration" in output_str:
            return True
        time.sleep(0.5)

    return False


def remove_server_from_velocity(server_name: str) -> bool:
    """Entfernt einen Server aus der velocity.toml und löst Reload aus."""
    velocity_dir = _get_velocity_instance_dir()
    if not velocity_dir:
        return False

    toml_path = velocity_dir / "velocity.toml"
    backup_path = velocity_dir / "velocity.toml.backup"
    shutil.copy2(toml_path, backup_path)

    try:
        with open(toml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        out_lines = []
        in_servers_block = False

        for line in lines:
            if line.strip() == "[servers]":
                in_servers_block = True
                out_lines.append(line)
                continue

            if in_servers_block and line.strip().startswith("["):
                in_servers_block = False

            if in_servers_block and line.strip() and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                if key.lower() == server_name.lower():
                    continue

            out_lines.append(line)

        with open(toml_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)

        reload_velocity_proxy()
        return True
    except Exception as e:
        shutil.copy2(backup_path, toml_path)
        print(f"Error removing from velocity.toml: {e}")
        return False


def get_registered_servers() -> dict:
    """Liest alle aktuell in velocity.toml eingetragenen Server aus."""
    velocity_dir = _get_velocity_instance_dir()
    if not velocity_dir:
        return {}

    toml_path = velocity_dir / "velocity.toml"
    servers = {}

    try:
        with open(toml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_servers_block = False
        for line in lines:
            if line.strip() == "[servers]":
                in_servers_block = True
                continue

            if in_servers_block and line.strip().startswith("["):
                break

            if in_servers_block and line.strip() and not line.strip().startswith("#"):
                parts = line.split("=")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    servers[key] = val

        return servers
    except Exception:
        return {}
