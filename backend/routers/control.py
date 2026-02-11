"""WebSocket endpoint for the Chainlit control interface (puppeteer console).

The puppeteer connects via WebSocket and sends slash commands.
The backend parses commands, queues them, and sends status updates back.
"""

import logging
from typing import Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# Active control WebSocket connections
_control_connections: Set[WebSocket] = set()


async def send_to_control(message: dict):
    """Send a message to all connected control interfaces."""
    disconnected = set()
    for ws in _control_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)

    for ws in disconnected:
        _control_connections.discard(ws)


@router.websocket("/ws/control")
async def control_websocket(websocket: WebSocket):
    """WebSocket endpoint for the Chainlit control interface.

    Receives slash commands from the puppeteer and sends back
    status updates, confirmations, and error messages.
    """
    await websocket.accept()
    _control_connections.add(websocket)
    logger.info(f"Control interface connected. Total: {len(_control_connections)}")

    try:
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "Control interface connected to DexIQ backend."},
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "command":
                raw_text = data.get("data", {}).get("text", "")
                logger.info(f"Received command: {raw_text}")

                # Import here to avoid circular imports
                from backend.main import handle_command
                result = await handle_command(raw_text)

                await websocket.send_json({
                    "type": "command_result",
                    "data": result,
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "data": {}})

    except WebSocketDisconnect:
        logger.info("Control interface disconnected.")
    except Exception as e:
        logger.error(f"Control WebSocket error: {e}")
    finally:
        _control_connections.discard(websocket)
        logger.info(f"Control connections remaining: {len(_control_connections)}")


def get_control_count() -> int:
    """Get the number of connected control interfaces."""
    return len(_control_connections)
