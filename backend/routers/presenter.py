"""WebSocket endpoint for the presenter screen (Reveal.js frontend).

The presenter screen connects via WebSocket and receives commands to:
- Advance/goto slides
- Play audio (pre-generated or live streamed)
- Show/hide avatar with different modes
- Display audience questions on screen
"""

import asyncio
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# Active presenter WebSocket connections
_presenter_connections: Set[WebSocket] = set()


async def broadcast_to_presenters(message: dict):
    """Broadcast a message to all connected presenter screens."""
    disconnected = set()
    for ws in _presenter_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)

    for ws in disconnected:
        _presenter_connections.discard(ws)


@router.websocket("/ws/presenter")
async def presenter_websocket(websocket: WebSocket):
    """WebSocket endpoint for the presenter screen.

    The presenter screen connects here and receives JSON messages
    with commands to control slides, audio, and avatar.
    """
    await websocket.accept()
    _presenter_connections.add(websocket)
    logger.info(f"Presenter screen connected. Total: {len(_presenter_connections)}")

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "Presenter screen connected to DexIQ backend."},
        })

        # Keep connection alive and listen for events from presenter
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "audio_ended":
                # Presenter reports audio playback finished
                logger.info("Audio playback ended on presenter screen.")
                playback_token = data.get("data", {}).get("playbackToken")
                # Import here to avoid circular imports
                from backend.main import handle_audio_complete
                await handle_audio_complete(playback_token=playback_token)

            elif msg_type == "slide_changed":
                slide_index = data.get("data", {}).get("slideIndex", 0)
                logger.info(f"Presenter reports slide changed to {slide_index}.")

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "data": {}})

    except WebSocketDisconnect:
        logger.info("Presenter screen disconnected.")
    except Exception as e:
        logger.error(f"Presenter WebSocket error: {e}")
    finally:
        _presenter_connections.discard(websocket)
        logger.info(f"Presenter connections remaining: {len(_presenter_connections)}")


def get_presenter_count() -> int:
    """Get the number of connected presenter screens."""
    return len(_presenter_connections)
