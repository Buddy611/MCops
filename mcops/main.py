import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException, UploadFile, File  # pyrefly: ignore[missing-import]
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse  # pyrefly: ignore[missing-import]
from fastapi.templating import Jinja2Templates  # pyrefly: ignore[missing-import]
from fastapi.staticfiles import StaticFiles  # pyrefly: ignore[missing-import]
from pydantic import BaseModel  # pyrefly: ignore[missing-import]
from pathlib import Path

from mcops.config import TEMPLATES_DIR as TPL_DIR, MCOPS_DIR, INSTANCES_DIR, PLUGIN_POOL_DIR
from mcops.modules import server_creator, plugin_manager, version_fetcher, stats_manager, file_manager
from mcops.api.websocket_terminal import router as ws_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mcops")


async def stats_task():
    while True:
        try:
            await stats_manager.aggregate_player_stats()
        except Exception as e:
            log.error(f"Stats task error: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(stats_task())
    yield
    task.cancel()


app = FastAPI(title="MCOps Panel", lifespan=lifespan)
app.include_router(ws_router)

# Static files (css, js, icons)
static_dir = MCOPS_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(MCOPS_DIR / "templates"))


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    registry = server_creator.load_registry()
    statuses = server_creator.get_all_statuses(registry)
    for name, info in registry.items():
        info["status"] = statuses.get(name, "offline")
    return templates.TemplateResponse(
        request=request, name="dashboard.html",
        context={"servers": registry, "active_page": "dashboard"}
    )


# ─────────────────────────────────────────────
# CREATE SERVER
# ─────────────────────────────────────────────

@app.get("/create", response_class=HTMLResponse)
async def create_server_form(request: Request):
    pool_plugins = plugin_manager.list_pool_plugins()
    paper_versions = []
    try:
        paper_versions = version_fetcher.get_paper_versions()
    except Exception:
        pass
    return templates.TemplateResponse(
        request=request, name="create_server.html",
        context={"plugins": pool_plugins, "paper_versions": paper_versions, "active_page": "create"}
    )


@app.post("/create", response_class=HTMLResponse)
async def create_server_submit(
    request: Request,
    server_name: str = Form(...),
    software: str = Form(...),
    version: str = Form(...),
    ram_gb: int = Form(...),
    port: str = Form("auto"),
    plugins: list[str] = Form([]),
):
    try:
        server_creator.create_server(
            server_name=server_name,
            software=software,
            version=version,
            ram_gb=ram_gb,
            port=port,
            plugins=plugins,
            start_after_creation=True,
        )
        return HTMLResponse(
            content='<div class="alert alert-success">✅ Server erfolgreich erstellt und gestartet! '
                    '<a href="/">Zum Dashboard</a></div>'
        )
    except Exception as e:
        return HTMLResponse(
            content=f'<div class="alert alert-danger">❌ Fehler: {e}</div>'
        )


@app.get("/api/versions/{software}")
async def api_get_versions(software: str):
    try:
        if software.lower() == "paper":
            return version_fetcher.get_paper_versions()
        elif software.lower() == "velocity":
            return version_fetcher.get_velocity_versions()
        elif software.lower() == "fabric":
            return version_fetcher.get_fabric_versions()
    except Exception:
        pass
    return []


# ─────────────────────────────────────────────
# SERVER DETAIL
# ─────────────────────────────────────────────

@app.get("/server/{name}", response_class=HTMLResponse)
async def server_detail(request: Request, name: str):
    registry = server_creator.load_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail="Server not found")
    info = registry[name]
    info["status"] = server_creator.get_server_status(name)
    return templates.TemplateResponse(
        request=request, name="server_detail.html",
        context={"name": name, "info": info, "active_page": "servers"}
    )


@app.post("/server/{name}/action")
async def server_action(name: str, action: str = Form(...)):
    registry = server_creator.load_registry()
    if name not in registry:
        return JSONResponse({"error": "Server not found"}, status_code=404)

    info = registry[name]
    software = info.get("software", "paper")
    ram_gb = info.get("ram_gb", 2)

    if action == "start":
        ok = server_creator.start_server_tmux(name, ram_gb, software)
        return JSONResponse({"status": "online" if ok else "offline"})
    elif action == "stop":
        ok = server_creator.stop_server_tmux(name, software)
        return JSONResponse({"status": "stopping"})
    elif action == "restart":
        ok = server_creator.restart_server_tmux(name, ram_gb, software)
        return JSONResponse({"status": "online" if ok else "offline"})
    elif action == "kill":
        from mcops.modules.server_creator import _get_tmux_server
        tmux = _get_tmux_server()
        if tmux:
            try:
                session = tmux.sessions.get(session_name=f"mc_{name}")
                if session:
                    session.kill_session()
            except Exception:
                pass
        return JSONResponse({"status": "offline"})

    return JSONResponse({"error": "Unknown action"}, status_code=400)


@app.delete("/server/{name}")
async def delete_server(name: str, keep_files: bool = False):
    try:
        server_creator.delete_server(name, remove_files=not keep_files)
        return JSONResponse({"status": "deleted"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/server/{name}/backup")
async def backup_server(name: str):
    try:
        path = server_creator.backup_server(name)
        return JSONResponse({"status": "ok", "backup_path": path})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# SERVER STATUS (HTMX polling)
# ─────────────────────────────────────────────

@app.get("/server/{name}/status", response_class=HTMLResponse)
async def get_server_status_badge(name: str):
    status = server_creator.get_server_status(name)
    color = "#22c55e" if status == "online" else "#ef4444"
    label = "Online" if status == "online" else "Offline"
    return HTMLResponse(
        f'<span class="badge" style="background:{color}20;color:{color};border:1px solid {color}50">'
        f'<span class="dot" style="background:{color}"></span>{label}</span>'
    )


# ─────────────────────────────────────────────
# FILE MANAGER
# ─────────────────────────────────────────────

@app.get("/server/{name}/files", response_class=HTMLResponse)
async def file_manager_view(request: Request, name: str, path: str = "/"):
    registry = server_creator.load_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        items = file_manager.list_directory(name, path)
    except Exception as e:
        items = []

    # Breadcrumb parts
    parts = [p for p in path.strip("/").split("/") if p]
    breadcrumbs = []
    acc = ""
    for p in parts:
        acc += f"/{p}"
        breadcrumbs.append({"name": p, "path": acc})

    info = registry[name]
    info["status"] = server_creator.get_server_status(name)

    return templates.TemplateResponse(
        request=request, name="file_manager.html",
        context={
            "name": name, "info": info,
            "items": items, "current_path": path,
            "breadcrumbs": breadcrumbs,
            "active_page": "servers"
        }
    )


@app.get("/server/{name}/files/read")
async def read_file(name: str, path: str):
    try:
        content = file_manager.read_file(name, path)
        return JSONResponse({"content": content})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/server/{name}/files/write")
async def write_file(name: str, path: str = Form(...), content: str = Form(...)):
    try:
        file_manager.write_file(name, path, content)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/server/{name}/files/upload")
async def upload_file(name: str, path: str = Form("/"), file: UploadFile = File(...)):
    try:
        data = await file.read()
        file_manager.upload_file(name, path, data, file.filename)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/server/{name}/files/delete")
async def delete_file(name: str, path: str):
    try:
        file_manager.delete_path(name, path)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────
# PLUGIN POOL
# ─────────────────────────────────────────────

@app.get("/plugins", response_class=HTMLResponse)
async def plugin_pool_view(request: Request):
    plugins = plugin_manager.list_pool_plugins()
    return templates.TemplateResponse(
        request=request, name="plugins.html",
        context={"plugins": plugins, "active_page": "plugins"}
    )


@app.post("/plugins/upload")
async def upload_plugin(file: UploadFile = File(...)):
    if not file.filename.endswith(".jar"):
        raise HTTPException(status_code=400, detail="Only .jar files allowed")
    data = await file.read()
    plugin_manager.save_uploaded_plugin(file.filename, data)
    return JSONResponse({"status": "ok", "filename": file.filename})


@app.delete("/plugins/{filename}")
async def delete_plugin(filename: str):
    ok = plugin_manager.delete_pool_plugin(filename)
    if not ok:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return JSONResponse({"status": "deleted"})


# ─────────────────────────────────────────────
# SERVER SETTINGS EDITOR
# ─────────────────────────────────────────────

@app.get("/server/{name}/settings", response_class=HTMLResponse)
async def server_settings(request: Request, name: str):
    registry = server_creator.load_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail="Server not found")
    info = registry[name]
    info["status"] = server_creator.get_server_status(name)

    # Read current server.properties if exists
    props: dict[str, str] = {}
    instance_dir = INSTANCES_DIR / name
    props_file = instance_dir / "server.properties"
    if props_file.exists():
        for line in props_file.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                props[k.strip()] = v.strip()

    return templates.TemplateResponse(
        request=request, name="server_settings.html",
        context={"name": name, "info": info, "props": props, "active_page": "servers"}
    )


@app.post("/server/{name}/settings")
async def save_server_settings(
    name: str,
    ram_gb: int = Form(...),
    port: int = Form(...),
    online_mode: str = Form("false"),
    motd: str = Form(""),
    max_players: int = Form(20),
    view_distance: int = Form(10),
    difficulty: str = Form("normal"),
    gamemode: str = Form("survival"),
    pvp: str = Form("true"),
):
    registry = server_creator.load_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail="Server not found")

    # Update registry (RAM)
    registry[name]["ram_gb"] = ram_gb
    registry[name]["port"] = port
    server_creator.save_registry(registry)

    # Write server.properties
    instance_dir = INSTANCES_DIR / name
    if instance_dir.exists():
        props = (
            f"server-port={port}\n"
            f"online-mode={online_mode}\n"
            f"motd={motd}\n"
            f"max-players={max_players}\n"
            f"view-distance={view_distance}\n"
            f"difficulty={difficulty}\n"
            f"gamemode={gamemode}\n"
            f"pvp={pvp}\n"
        )
        (instance_dir / "server.properties").write_text(props, encoding="utf-8")

    return JSONResponse({"status": "ok", "message": "Einstellungen gespeichert. Server neustarten um Änderungen zu übernehmen."})



# ─────────────────────────────────────────────
# AUTOMATION API (external access)
# ─────────────────────────────────────────────

class CreateServerRequest(BaseModel):
    api_key: str
    server_name: str
    software: str
    version: str
    ram_gb: int
    port: str | int = "auto"
    plugins: list[str] = []
    template: str | None = None
    start_after_creation: bool = True


@app.post("/api/server/create")
async def api_create_server(req: CreateServerRequest):
    import os
    valid_key = os.environ.get("MCOPS_API_KEY", "changeme")
    if req.api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    try:
        res = server_creator.create_server(
            server_name=req.server_name,
            software=req.software,
            version=req.version,
            ram_gb=req.ram_gb,
            port=req.port,
            plugins=req.plugins,
            template=req.template,
            start_after_creation=req.start_after_creation,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ServerActionRequest(BaseModel):
    api_key: str
    action: str

@app.post("/api/server/{name}/action")
async def api_server_action(name: str, req: ServerActionRequest):
    import os
    valid_key = os.environ.get("MCOPS_API_KEY", "changeme")
    if req.api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    registry = server_creator.load_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail="Server not found")
        
    info = registry[name]
    software = info.get("software", "paper")
    ram_gb = info.get("ram_gb", 2)
    
    if req.action == "start":
        ok = server_creator.start_server_tmux(name, ram_gb, software)
        return {"status": "online" if ok else "offline"}
    elif req.action == "stop":
        server_creator.stop_server_tmux(name, software)
        return {"status": "stopping"}
    elif req.action == "restart":
        ok = server_creator.restart_server_tmux(name, ram_gb, software)
        return {"status": "online" if ok else "offline"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# ─────────────────────────────────────────────
# DATABASE MANAGEMENT
# ─────────────────────────────────────────────

@app.get("/database", response_class=HTMLResponse)
async def database_view(request: Request):
    from mcops.modules.db_injector import load_db_config
    db_config = load_db_config()
    return templates.TemplateResponse(
        request=request, name="database.html",
        context={"db_config": db_config, "active_page": "database"}
    )


@app.post("/database/save")
async def save_db_config(
    db_host: str = Form("127.0.0.1"),
    db_port: str = Form("3306"),
    db_user: str = Form(...),
    db_password: str = Form(...),
    db_name: str = Form(...),
):
    from mcops.config import DB_CONFIG_FILE
    content = (
        f"DB_HOST={db_host}\n"
        f"DB_PORT={db_port}\n"
        f"DB_USER={db_user}\n"
        f"DB_PASSWORD={db_password}\n"
        f"DB_NAME={db_name}\n"
    )
    DB_CONFIG_FILE.write_text(content, encoding="utf-8")
    return JSONResponse({"status": "ok", "message": "Datenbankverbindung gespeichert."})


@app.post("/database/test")
async def test_db_connection(
    db_host: str = Form("127.0.0.1"),
    db_port: str = Form("3306"),
    db_user: str = Form(...),
    db_password: str = Form(...),
    db_name: str = Form(...),
):
    import socket
    try:
        sock = socket.create_connection((db_host, int(db_port)), timeout=3)
        sock.close()
        return JSONResponse({"status": "ok", "message": f"Verbindung zu {db_host}:{db_port} erfolgreich."})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=200)


# ─────────────────────────────────────────────
# PLUGIN EVENT API  (called by MCOps Spigot plugin)
# ─────────────────────────────────────────────

class PlayerEventRequest(BaseModel):
    api_key: str
    player: str
    event: str      # "join" or "quit"
    server: str

@app.post("/api/stats/event")
async def record_player_event(req: PlayerEventRequest):
    """Called by the MCOps plugins on player join/quit."""
    import os
    valid_key = os.environ.get("MCOPS_API_KEY", "changeme")
    if req.api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    if req.event not in ("join", "quit"):
        raise HTTPException(status_code=400, detail="event must be 'join' or 'quit'")
    from datetime import datetime
    stats_manager.record_event(req.player, req.event, req.server, datetime.now())
    return {"status": "ok"}


@app.get("/api/stats")
async def get_stats(api_key: str = ""):
    import os
    valid_key = os.environ.get("MCOPS_API_KEY", "changeme")
    if api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    return {
        "current_players": stats_manager.get_current_player_count(),
        "online_players":  stats_manager.get_online_players(),
        "per_server":      stats_manager.get_players_per_server(),
        "peak_today":      stats_manager.get_peak_today(),
        "timeseries":      stats_manager.get_timeseries(24),
        "recent_events":   stats_manager.get_recent_events(20),
    }
