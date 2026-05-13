import json
import urllib.request
from cachetools import cached, TTLCache  # pyrefly: ignore[missing-import]

# Cache for 6 hours (21600 seconds), max 10 items
cache = TTLCache(maxsize=10, ttl=21600)

@cached(cache)
def get_paper_versions() -> list[str]:
    url = "https://api.papermc.io/v2/projects/paper"
    req = urllib.request.Request(url, headers={'User-Agent': 'Buddy611/2.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        return data.get("versions", [])

@cached(cache)
def get_velocity_versions() -> list[str]:
    url = "https://api.papermc.io/v2/projects/velocity"
    req = urllib.request.Request(url, headers={'User-Agent': 'Buddy611/2.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        return data.get("versions", [])

@cached(cache)
def get_fabric_versions() -> list[str]:
    url = "https://meta.fabricmc.net/v2/versions/game"
    req = urllib.request.Request(url, headers={'User-Agent': 'Buddy611/2.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        # Filter for stable versions
        return [v["version"] for v in data if v.get("stable", True)]

def get_latest_build_url(software: str, version: str) -> str:
    """Gets the direct download URL for the jar."""
    if software.lower() == "paper":
        return _get_papermc_build_url("paper", version)
    elif software.lower() == "velocity":
        return _get_papermc_build_url("velocity", version)
    elif software.lower() == "fabric":
        loader_url = "https://meta.fabricmc.net/v2/versions/loader"
        req = urllib.request.Request(loader_url, headers={'User-Agent': 'Buddy611/2.0'})
        with urllib.request.urlopen(req) as response:
            loader_data = json.loads(response.read().decode())
            latest_loader = loader_data[0]["version"]
            
        installer_url = "https://meta.fabricmc.net/v2/versions/installer"
        req = urllib.request.Request(installer_url, headers={'User-Agent': 'Buddy611/2.0'})
        with urllib.request.urlopen(req) as response:
            installer_data = json.loads(response.read().decode())
            latest_installer = installer_data[0]["version"]
            
        return f"https://meta.fabricmc.net/v2/versions/loader/{version}/{latest_loader}/{latest_installer}/server/jar"
    return ""

def _get_papermc_build_url(project: str, version: str) -> str:
    url = f"https://api.papermc.io/v2/projects/{project}/versions/{version}/builds"
    req = urllib.request.Request(url, headers={'User-Agent': 'Buddy611/2.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        builds = data.get("builds", [])
        if not builds:
            raise ValueError(f"No builds found for {project} {version}")
        latest_build = builds[-1]
        build_id = latest_build["build"]
        download_name = latest_build["downloads"]["application"]["name"]
        return f"https://api.papermc.io/v2/projects/{project}/versions/{version}/builds/{build_id}/downloads/{download_name}"

def download_jar(url: str, dest_path: str):
    req = urllib.request.Request(url, headers={'User-Agent': 'Buddy611/2.0'})
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        out_file.write(response.read())
