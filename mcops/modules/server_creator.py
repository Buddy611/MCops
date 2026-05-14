import os
import sys
import json
import logging
import shutil
from pathlib import Path

# libtmux is Linux-only
if sys.platform != "win32":
    try:
        import libtmux as _libtmux  # pyrefly: ignore[missing-import]
        _LIBTMUX_AVAILABLE = True
    except ImportError:
        _LIBTMUX_AVAILABLE = False
else:
    _LIBTMUX_AVAILABLE = False

from mcops.config import INSTANCES_DIR, TEMPLATES_DIR, SERVER_REGISTRY_FILE, BACKUPS_DIR, DB_CONFIG_FILE
from mcops.modules.version_fetcher import get_latest_build_url, download_jar
from mcops.modules.plugin_manager import copy_plugin_to_instance
from mcops.modules.db_injector import inject_database_credentials
from mcops.modules.velocity_manager import register_server_in_velocity, reload_velocity_proxy, remove_server_from_velocity

log = logging.getLogger("server_creator")


def _get_tmux_server():
    if _LIBTMUX_AVAILABLE:
        import libtmux
        return libtmux.Server()
    return None


def load_registry() -> dict:
    if SERVER_REGISTRY_FILE.exists():
        with open(SERVER_REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_registry(data: dict):
    with open(SERVER_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def find_available_port(start_port=25570) -> int:
    registry = load_registry()
    used_ports = {info.get("port") for info in registry.values()}
    port = start_port
    while port in used_ports:
        port += 1
    return port


def _find_session(tmux, session_name: str):
    """Safely find a tmux session by name."""
    try:
        for s in tmux.sessions:
            if s.name == session_name:
                return s
    except Exception:
        pass
    return None


def get_server_status(name: str) -> str:
    """Returns 'online' or 'offline'."""
    tmux = _get_tmux_server()
    if not tmux:
        return "offline"
    return "online" if _find_session(tmux, f"mc_{name}") else "offline"


def get_all_statuses(registry: dict) -> dict:
    """Returns status for all servers in one tmux call."""
    tmux = _get_tmux_server()
    if not tmux:
        return {name: "offline" for name in registry}
    try:
        active_sessions = {s.name for s in tmux.sessions}
    except Exception:
        active_sessions = set()
    return {
        name: ("online" if f"mc_{name}" in active_sessions else "offline")
        for name in registry
    }


def create_server(
    server_name: str,
    software: str,
    version: str,
    ram_gb: int,
    port: str | int,
    plugins: list[str],
    template: str | None = None,
    start_after_creation: bool = True,
) -> dict:

    # 1. Port
    if port == "auto" or port == 0:
        port = find_available_port()
    else:
        port = int(port)

    # 2. Directory
    instance_dir = INSTANCES_DIR / server_name
    if instance_dir.exists():
        raise FileExistsError(f"Server directory '{server_name}' already exists.")
    instance_dir.mkdir(parents=True)

    # 3. Download JAR
    jar_url = get_latest_build_url(software, version)
    if not jar_url:
        shutil.rmtree(instance_dir, ignore_errors=True)
        raise ValueError(f"Could not find download URL for {software} {version}")

    jar_path = instance_dir / "server.jar"
    try:
        download_jar(jar_url, str(jar_path))
    except Exception as e:
        shutil.rmtree(instance_dir, ignore_errors=True)
        raise RuntimeError(f"JAR download failed: {e}")

    # 4. EULA + server.properties
    (instance_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")

    props_content = f"server-port={port}\nonline-mode=false\n"
    if software.lower() == "velocity":
        # Velocity proxy doesn't use server.properties
        pass
    else:
        (instance_dir / "server.properties").write_text(props_content, encoding="utf-8")

    # 5. Template
    if template:
        template_dir = TEMPLATES_DIR / template
        if template_dir.exists():
            for item in template_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, instance_dir / item.name)

    # 6. Plugins
    is_mod = (software.lower() == "fabric")
    for plugin in plugins:
        copy_plugin_to_instance(plugin, server_name, is_mod=is_mod)
        
    # 7. DB Injection
    inject_database_credentials(server_name)
    
    # 7.5 Global Database Credentials (available to all plugins/scripts in server root)
    if DB_CONFIG_FILE.exists():
        shutil.copy2(DB_CONFIG_FILE, instance_dir / ".env")

    # 8. Registry
    registry = load_registry()
    registry[server_name] = {
        "software": software,
        "version": version,
        "ram_gb": ram_gb,
        "port": port,
        "plugins": plugins,
    }
    save_registry(registry)

    # 9. Start
    if start_after_creation:
        start_server_tmux(server_name, ram_gb, software)

    # 10. Velocity auto-register (skip for Velocity itself)
    if software.lower() != "velocity":
        velocity_ok = register_server_in_velocity(server_name, "127.0.0.1", port)
        if velocity_ok:
            reload_velocity_proxy()

    return {"status": "success", "server_name": server_name, "port": port}


def start_server_tmux(server_name: str, ram_gb: int, software: str = "paper") -> bool:
    instance_dir = INSTANCES_DIR / server_name
    if not instance_dir.exists():
        log.error(f"Instance dir missing: {instance_dir}")
        return False

    tmux = _get_tmux_server()
    if not tmux:
        log.warning("libtmux not available – cannot start server.")
        return False

    session_name = f"mc_{server_name}"
    if _find_session(tmux, session_name):
        log.info(f"{server_name} already running.")
        return True

    # Resolve java binary
    import shutil as _shutil
    java_bin = _shutil.which("java") or "/usr/bin/java"

    cmd = (
        f"cd '{instance_dir}' && "
        f"{java_bin} -Xmx{ram_gb}G -Xms512M "
        f"-XX:+UseG1GC -XX:+ParallelRefProcEnabled "
        f"-jar server.jar nogui; "
        f"echo '[MCOps] Process exited with code $?'"
    )

    try:
        tmux.new_session(
            session_name=session_name,
            window_name=server_name,
            window_command=cmd,
            attach=False,  # run detached – do NOT use detach=True (wrong param)
        )
        log.info(f"Started {server_name} in tmux session '{session_name}'")
        return True
    except Exception as e:
        log.error(f"tmux.new_session failed for {server_name}: {e}")
        return False


def stop_server_tmux(server_name: str, software: str = "paper") -> bool:
    tmux = _get_tmux_server()
    if not tmux:
        return False

    session = _find_session(tmux, f"mc_{server_name}")
    if not session:
        return False

    try:
        pane = session.attached_window.attached_pane
        pane.send_keys("end" if software.lower() == "velocity" else "stop")
        return True
    except Exception as e:
        log.error(f"stop_server_tmux error: {e}")
        return False


def kill_server_tmux(server_name: str) -> bool:
    tmux = _get_tmux_server()
    if not tmux:
        return False
    session = _find_session(tmux, f"mc_{server_name}")
    if session:
        try:
            session.kill_session()
            return True
        except Exception as e:
            log.error(f"kill_server_tmux error: {e}")
            return False
    return False


def restart_server_tmux(server_name: str, ram_gb: int, software: str = "paper") -> bool:
    stop_server_tmux(server_name, software)
    import time as _time
    _time.sleep(4)
    return start_server_tmux(server_name, ram_gb, software)


def delete_server(server_name: str, remove_files: bool = True) -> bool:
    registry = load_registry()
    if server_name not in registry:
        raise KeyError(f"Server '{server_name}' not found in registry.")

    info = registry[server_name]

    # Stop if running
    stop_server_tmux(server_name, info.get("software", "paper"))

    # Remove from Velocity
    remove_server_from_velocity(server_name)

    # Delete files
    if remove_files:
        instance_dir = INSTANCES_DIR / server_name
        if instance_dir.exists():
            shutil.rmtree(instance_dir)

    del registry[server_name]
    save_registry(registry)
    return True


def backup_server(server_name: str) -> str:
    """Creates a zip backup of the server directory. Returns the backup path."""
    instance_dir = INSTANCES_DIR / server_name
    if not instance_dir.exists():
        raise FileNotFoundError(f"Server directory not found: {server_name}")

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{server_name}_{timestamp}"
    backup_zip = BACKUPS_DIR / backup_name

    shutil.make_archive(str(backup_zip), "zip", str(instance_dir))
    return str(backup_zip) + ".zip"
