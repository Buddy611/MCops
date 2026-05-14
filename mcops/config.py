import os
import sys
from pathlib import Path

VERSION = "2.0.3"

# The base directory where all server data resides.
# In production, this is usually /opt/mcops.
DEFAULT_BASE = "/opt/mcops" if sys.platform != "win32" else str(Path.home() / "Desktop" / "Programmieren" / "Minecraft" / "Server Software")
BASE_DIR = Path(os.environ.get("MCOPS_BASE_DIR", DEFAULT_BASE)).resolve()

INSTANCES_DIR = BASE_DIR / "instances"
PLUGIN_POOL_DIR = BASE_DIR / "plugin-pool"
TEMPLATES_DIR = BASE_DIR / "templates"
BACKUPS_DIR = BASE_DIR / "backups"
GLOBAL_DIR = BASE_DIR / "global"

DB_CONFIG_FILE = GLOBAL_DIR / "db_config.env"
SERVER_REGISTRY_FILE = GLOBAL_DIR / "server_registry.json"
INJECTION_RULES_FILE = GLOBAL_DIR / "injection_rules.json"
PLUGIN_TEMPLATES_DIR = GLOBAL_DIR / "plugin-templates"
STATS_DB_FILE = GLOBAL_DIR / "stats.db"
MCOPS_DIR = Path(__file__).parent.resolve()

# Ensure core directories exist
for directory in [
    INSTANCES_DIR, PLUGIN_POOL_DIR, TEMPLATES_DIR, 
    BACKUPS_DIR, GLOBAL_DIR, PLUGIN_TEMPLATES_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)
