import os
import json
from pathlib import Path
from jinja2 import Template  # pyrefly: ignore[missing-import]
from mcops.config import (
    GLOBAL_DIR, DB_CONFIG_FILE, INSTANCES_DIR, 
    PLUGIN_TEMPLATES_DIR, INJECTION_RULES_FILE
)

def load_db_config() -> dict:
    config = {}
    if DB_CONFIG_FILE.exists():
        with open(DB_CONFIG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    return config

def get_injection_rules() -> dict:
    if INJECTION_RULES_FILE.exists():
        with open(INJECTION_RULES_FILE, "r") as f:
            return json.load(f)
    return {}

def inject_database_credentials(server_name: str):
    """
    Scans the server instance for known plugins and injects the database credentials 
    using Jinja2 templates.
    """
    db_config = load_db_config()
    if not db_config:
        return # No global DB config to inject
        
    rules = get_injection_rules()
    instance_dir = INSTANCES_DIR / server_name
    
    for plugin_path_str, template_name in rules.items():
        # plugin_path_str like "plugins/LuckPerms/config.yml"
        target_path = instance_dir / plugin_path_str
        template_file = PLUGIN_TEMPLATES_DIR / template_name
        
        if template_file.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(template_file, "r", encoding="utf-8") as tf:
                template_content = tf.read()
                
            jinja_template = Template(template_content)
            rendered = jinja_template.render(**db_config)
            
            with open(target_path, "w", encoding="utf-8") as out:
                out.write(rendered)
