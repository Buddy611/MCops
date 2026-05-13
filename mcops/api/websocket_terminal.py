import sys
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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


@router.websocket("/ws/terminal/{server_name}")
async def terminal_endpoint(websocket: WebSocket, server_name: str):
    await websocket.accept()

    tmux = _get_tmux_server()
    if not tmux:
        await websocket.send_text("[MCOps] tmux not available on this system.\r\n")
        await websocket.close()
        return

    session_name = f"mc_{server_name}"
    try:
        session = tmux.sessions.get(session_name=session_name)
    except Exception:
        session = None

    if not session:
        await websocket.send_text(
            f"[MCOps] Server '{server_name}' is not running or tmux session not found.\r\n"
        )
        await websocket.close()
        return

    pane = session.attached_window.attached_pane

    async def read_tmux_output():
        last_lines: list[str] = []
        while True:
            try:
                output: list[str] = pane.cmd("capture-pane", "-p").stdout
                if output != last_lines:
                    # Send only newly added lines
                    if len(output) >= len(last_lines):
                        new_content = output[len(last_lines):]
                    else:
                        new_content = output  # full refresh on wrap

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

    output_task = asyncio.create_task(read_tmux_output())
    input_task = asyncio.create_task(read_websocket_input())

    try:
        await asyncio.gather(input_task, output_task)
    except Exception:
        pass
    finally:
        output_task.cancel()
        input_task.cancel()
