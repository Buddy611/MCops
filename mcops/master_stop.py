import sys
import time
import json
import logging

if sys.platform != "win32":
    try:
        import libtmux as _libtmux  # pyrefly: ignore[missing-import]
        _LIBTMUX_AVAILABLE = True
    except ImportError:
        _LIBTMUX_AVAILABLE = False
else:
    _LIBTMUX_AVAILABLE = False

from mcops.config import SERVER_REGISTRY_FILE

log = logging.getLogger("master_stop")

def stop_all_servers(timeout_seconds=60):
    """
    Sicheres Herunterfahren aller laufenden tmux-Instanzen anhand der server_registry.json
    """
    if not _LIBTMUX_AVAILABLE:
        log.error("libtmux nicht verfügbar – kann Server nicht stoppen.")
        return

    if not SERVER_REGISTRY_FILE.exists():
        log.info("Keine server_registry.json gefunden. Nichts zu stoppen.")
        return

    with open(SERVER_REGISTRY_FILE, "r", encoding="utf-8") as f:
        registry = json.load(f)

    server_libtmux = _libtmux.Server()

    # Send /stop to all known servers
    for server_name in registry.keys():
        session_name = f"mc_{server_name}"
        try:
            session = server_libtmux.sessions.get(session_name=session_name)
            if session:
                log.info(f"Sende Stop-Befehl an {server_name}...")
                pane = session.attached_window.attached_pane
                software = registry[server_name].get("software", "paper")
                if software.lower() == "velocity":
                    pane.send_keys("end")
                else:
                    pane.send_keys("stop")
        except Exception as e:
            log.warning(f"Fehler beim Stoppen von {server_name}: {e}")
            
    # Wait for all sessions to close
    log.info(f"Warte bis zu {timeout_seconds} Sekunden auf das Beenden der Server...")
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        all_closed = True
        for server_name in registry.keys():
            session_name = f"mc_{server_name}"
            try:
                if server_libtmux.sessions.get(session_name=session_name):
                    all_closed = False
                    break
            except Exception:
                pass
                
        if all_closed:
            log.info("Alle Server wurden erfolgreich gestoppt.")
            return
            
        time.sleep(2)
        
    # Kill remaining
    log.warning("Timeout erreicht. Erzwinge das Beenden verbleibender Sessions...")
    for server_name in registry.keys():
        session_name = f"mc_{server_name}"
        try:
            session = server_libtmux.sessions.get(session_name=session_name)
            if session:
                log.warning(f"Kille {server_name}...")
                session.kill_session()
        except Exception:
            pass
            
    log.info("Master-Stop abgeschlossen.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stop_all_servers()
