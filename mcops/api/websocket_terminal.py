import sys
import asyncio
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from mcops.config import INSTANCES_DIR

router = APIRouter()

# libtmux is Linux-only
if sys.platform != "win32":
    try:
        import libtmux as _libtmux  # pyrefly: ignore[missing-import]
        _LIBTMUX_AVAILABLE = True
    except ImportError:
        _LIBTMUX_AVAILABLE = False
else:
    _LIBTMUX_AVAILABLE = False


def _get_tmux_server():
    if _LIBTMUX_AVAILABLE:
        import libtmux
        return libtmux.Server()
    return None


async def tail_log_file(websocket: WebSocket, log_path: str):
    """Tails a log file and sends new lines to the websocket."""
    if not os.path.exists(log_path):
        # Wait for file to be created
        for _ in range(10):
            if os.path.exists(log_path):
                break
            await asyncio.sleep(1)
        else:
            await websocket.send_text("[MCOps] Log file not found. Server might still be starting...\r\n")
            return

    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        # Go to end of file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.5)
                continue
            await websocket.send_text(line)


@router.websocket("/ws/terminal/{server_name}")
async def terminal_endpoint(websocket: WebSocket, server_name: str):
    await websocket.accept()

    log_path = INSTANCES_DIR / server_name / "logs" / "latest.log"
    
    tmux = _get_tmux_server()
    session_name = f"mc_{server_name}"
    session = None
    
    if tmux:
        try:
            session = tmux.sessions.get(session_name=session_name)
        except Exception:
            session = None

    # If we have a tmux session, we can send input AND read output
    if session:
        pane = session.attached_window.attached_pane

        async def read_tmux_output():
            last_lines: list[str] = []
            while True:
                try:
                    output: list[str] = pane.cmd("capture-pane", "-p").stdout
                    if output != last_lines:
                        if len(output) >= len(last_lines):
                            new_content = output[len(last_lines):]
                        else:
                            new_content = output
                        for line in new_content:
                            await websocket.send_text(line + "\r\n")
                        last_lines = output
                    await asyncio.sleep(0.3)
                except Exception:
                    break

        async def read_websocket_input():
            try:
                while True:
                    data = await websocket.receive_text()
                    pane.send_keys(data, enter=True)
            except WebSocketDisconnect:
                pass

        tasks = [
            asyncio.create_task(read_tmux_output()),
            asyncio.create_task(read_websocket_input())
        ]
        try:
            await asyncio.gather(*tasks)
        except Exception:
            pass
        finally:
            for t in tasks: t.cancel()
            
    else:
        # Fallback for Windows or no tmux: Read logs directly
        # Note: Input is not supported in simple process mode yet (needs stdin pipe)
        await websocket.send_text("[MCOps] Connected via Log-Stream (Input disabled in direct mode)\r\n")
        
        output_task = asyncio.create_task(tail_log_file(websocket, str(log_path)))
        
        try:
            # We still listen for disconnect
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            output_task.cancel()
