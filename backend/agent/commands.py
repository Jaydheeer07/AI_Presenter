"""Slash command parser and FIFO command queue."""

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Command:
    """A parsed slash command or free-text input."""
    type: str
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=None))
    priority: int = 0  # 0 = normal, 1 = interrupt (pause/stop)
    raw_text: str = ""


# Commands that bypass the queue and execute immediately
INTERRUPT_COMMANDS = {"pause", "stop"}

# All recognized slash commands
VALID_COMMANDS = {
    "intro", "start", "next", "prev", "goto", "ask", "example",
    "qa", "pick", "outro", "pause", "resume", "skip", "status",
}


def parse_command(text: str) -> Command:
    """Parse a slash command or free-text input into a Command object.

    Supported formats:
        /intro
        /start
        /next
        /prev
        /goto 5
        /ask Maria: What AI tools do you use?
        /pick 3
        /qa
        /outro
        /pause
        /resume
        /skip
        /status
        /example
        (free text) — treated as an answer summary
    """
    text = text.strip()

    if not text.startswith("/"):
        # Free text = answer summary from the puppeteer
        return Command(
            type="answer",
            payload={"summary": text},
            raw_text=text,
        )

    # Extract command name and arguments
    match = re.match(r"^/(\w+)\s*(.*)", text, re.DOTALL)
    if not match:
        return Command(type="unknown", payload={"error": f"Could not parse: {text}"}, raw_text=text)

    cmd_name = match.group(1).lower()
    args = match.group(2).strip()

    if cmd_name not in VALID_COMMANDS:
        return Command(type="unknown", payload={"error": f"Unknown command: /{cmd_name}"}, raw_text=text)

    priority = 1 if cmd_name in INTERRUPT_COMMANDS else 0
    payload = {}

    if cmd_name == "goto":
        try:
            payload["slide_number"] = int(args)
        except ValueError:
            return Command(
                type="error",
                payload={"error": f"/goto requires a slide number, got: '{args}'"},
                raw_text=text,
            )

    elif cmd_name == "ask":
        # Format: /ask Name: Question
        ask_match = re.match(r"^(\w+):\s*(.+)", args, re.DOTALL)
        if ask_match:
            payload["target_name"] = ask_match.group(1)
            payload["question"] = ask_match.group(2).strip()
        else:
            return Command(
                type="error",
                payload={"error": "Format: /ask Name: Your question here"},
                raw_text=text,
            )

    elif cmd_name == "pick":
        try:
            payload["question_id"] = int(args)
        except ValueError:
            return Command(
                type="error",
                payload={"error": f"/pick requires a question ID, got: '{args}'"},
                raw_text=text,
            )

    return Command(type=cmd_name, payload=payload, priority=priority, raw_text=text)


class CommandQueue:
    """FIFO command queue with interrupt support.

    Commands enter the queue and are processed one at a time.
    Interrupt commands (/pause, /stop) execute immediately.
    """

    def __init__(self):
        self._queue: deque[Command] = deque()
        self._current_action: Optional[Command] = None
        self._is_busy: bool = False
        self._on_command_callback = None
        self._on_interrupt_callback = None

    @property
    def is_busy(self) -> bool:
        return self._is_busy

    @property
    def current_action(self) -> Optional[Command]:
        return self._current_action

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    def set_callbacks(self, on_command=None, on_interrupt=None):
        """Set callback functions for command processing."""
        self._on_command_callback = on_command
        self._on_interrupt_callback = on_interrupt

    def enqueue(self, command: Command) -> dict:
        """Add a command to the queue. Interrupts execute immediately."""
        if command.priority == 1:
            return self._interrupt(command)

        self._queue.append(command)
        result = {
            "status": "queued",
            "command": command.type,
            "queue_position": len(self._queue),
            "queue_size": len(self._queue),
        }

        if not self._is_busy:
            return self.process_next()

        return result

    def _interrupt(self, command: Command) -> dict:
        """Handle an interrupt command (executes immediately)."""
        if self._on_interrupt_callback:
            return self._on_interrupt_callback(command)
        return {"status": "interrupt", "command": command.type}

    def process_next(self) -> dict:
        """Process the next command in the queue."""
        if not self._queue:
            self._is_busy = False
            self._current_action = None
            return {"status": "idle", "message": "Queue empty"}

        cmd = self._queue.popleft()
        self._is_busy = True
        self._current_action = cmd

        if self._on_command_callback:
            return self._on_command_callback(cmd)

        return {"status": "processing", "command": cmd.type}

    def on_action_complete(self) -> dict:
        """Called when the current action finishes. Processes next in queue."""
        self._is_busy = False
        self._current_action = None
        return self.process_next()

    def clear(self):
        """Clear all queued commands."""
        self._queue.clear()
        self._current_action = None
        self._is_busy = False

    def get_status(self) -> dict:
        """Get current queue status."""
        return {
            "is_busy": self._is_busy,
            "current_action": self._current_action.type if self._current_action else None,
            "queue_size": len(self._queue),
            "queued_commands": [cmd.type for cmd in self._queue],
        }
