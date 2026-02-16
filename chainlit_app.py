"""Chainlit control interface for the DexIQ AI Presenter.

This is the puppeteer's console — a chat UI where you type slash commands
to control the AI presenter. Runs as a separate process and communicates
with the FastAPI backend via WebSocket.
"""

import asyncio
import json
import logging
import os

import chainlit as cl
import websockets

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws/control")

# Global WebSocket connection
_ws_connection = None
_ws_listener_task = None


def _ws_is_open(ws) -> bool:
    """Check if a WebSocket connection is open (compatible with websockets v13+)."""
    if ws is None:
        return False
    try:
        return ws.open
    except AttributeError:
        pass
    try:
        from websockets.protocol import State
        return ws.protocol.state is State.OPEN
    except (AttributeError, ImportError):
        return False


async def _get_ws():
    """Get or create the WebSocket connection to the backend."""
    global _ws_connection
    if not _ws_is_open(_ws_connection):
        try:
            _ws_connection = await websockets.connect(BACKEND_WS_URL)
            logger.info(f"Connected to backend at {BACKEND_WS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to backend: {e}")
            raise
    return _ws_connection


async def _listen_for_updates():
    """Background task that listens for status updates from the backend."""
    while True:
        try:
            ws = await _get_ws()
            message = await ws.recv()
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "connected":
                await cl.Message(
                    content="✅ **Connected to DexIQ backend.**\n\nType `/intro` to begin the presentation.",
                    author="System",
                ).send()

            elif msg_type == "command_result":
                result = data.get("data", {})
                status = result.get("status", "")
                if status == "error":
                    await cl.Message(
                        content=f"❌ **Error:** {result.get('message', 'Unknown error')}",
                        author="System",
                    ).send()

            elif msg_type == "status_update":
                update = data.get("data", {})
                state = update.get("state", "")
                message_text = update.get("message", "")
                slide = update.get("slide", "")

                status_line = f"**State:** `{state}`"
                if slide:
                    status_line += f" | **Slide:** {slide}"
                if message_text:
                    status_line += f"\n{message_text}"

                await cl.Message(content=status_line, author="DexIQ").send()

            elif msg_type == "response_generated":
                resp = data.get("data", {})
                target = resp.get("target", "")
                response = resp.get("response", "")
                await cl.Message(
                    content=f"🗣️ **Response to {target}:**\n\n> {response}",
                    author="DexIQ",
                ).send()

            elif msg_type == "new_question":
                q = data.get("data", {})
                score = q.get("score", "?")
                flag = q.get("flag", "")
                flag_text = f" ⚠️ `{flag}`" if flag else ""
                await cl.Message(
                    content=f"❓ **New Q&A question** (#{q.get('id')}, score: {score}{flag_text}):\n"
                            f"**{q.get('name', 'Anonymous')}:** {q.get('question', '')}",
                    author="System",
                ).send()

            elif msg_type == "pong":
                pass  # Heartbeat response

        except (websockets.ConnectionClosed, websockets.exceptions.ConnectionClosedError):
            logger.warning("WebSocket connection closed. Reconnecting in 3s...")
            global _ws_connection
            _ws_connection = None
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Listener error: {e}")
            await asyncio.sleep(1)


@cl.on_chat_start
async def on_chat_start():
    """Called when the Chainlit chat session starts."""
    global _ws_listener_task

    await cl.Message(
        content="# 🎭 DexIQ Puppeteer Console\n\n"
                "Connecting to backend...\n\n"
                "**Quick Reference:**\n"
                "- `/intro` — AI introduces itself\n"
                "- `/start` — Begin slide narration\n"
                "- `/next` / `/prev` — Navigate slides\n"
                "- `/goto N` — Jump to slide N\n"
                "- `/ask Name: Question` — AI asks someone a question\n"
                "- *(type answer summary)* — AI responds to their answer\n"
                "- `/qa` — Enter Q&A mode\n"
                "- `/pick N` — Answer question #N\n"
                "- `/outro` — Closing remarks\n"
                "- `/pause` / `/resume` — Emergency controls\n"
                "- `/status` — Check current state\n"
                "- `/skip` — Skip current action\n",
        author="System",
    ).send()

    # Start background listener for backend updates
    _ws_listener_task = asyncio.create_task(_listen_for_updates())


@cl.on_message
async def on_message(message: cl.Message):
    """Called when the puppeteer sends a message (slash command or free text)."""
    text = message.content.strip()
    if not text:
        return

    try:
        ws = await _get_ws()
        await ws.send(json.dumps({
            "type": "command",
            "data": {"text": text},
        }))
        logger.info(f"Sent command: {text}")
    except Exception as e:
        await cl.Message(
            content=f"❌ **Connection error:** {e}\n\nIs the backend running?",
            author="System",
        ).send()


@cl.on_chat_end
async def on_chat_end():
    """Called when the chat session ends."""
    global _ws_connection, _ws_listener_task

    if _ws_listener_task:
        _ws_listener_task.cancel()

    if _ws_is_open(_ws_connection):
        await _ws_connection.close()
        logger.info("WebSocket connection closed.")
