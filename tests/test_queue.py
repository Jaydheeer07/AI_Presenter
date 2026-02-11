"""Tests for the command queue system."""

import pytest

from backend.agent.commands import Command, CommandQueue


class TestCommandQueue:
    """Test the FIFO command queue."""

    def test_empty_queue(self):
        q = CommandQueue()
        assert q.queue_size == 0
        assert q.is_busy is False
        assert q.current_action is None

    def test_enqueue_single(self):
        q = CommandQueue()
        cmd = Command(type="next", payload={})
        result = q.enqueue(cmd)
        # Without a callback, process_next returns processing status
        assert result["status"] == "processing" or result["status"] == "queued"

    def test_enqueue_while_busy(self):
        q = CommandQueue()
        q._is_busy = True
        cmd = Command(type="next", payload={})
        result = q.enqueue(cmd)
        assert result["status"] == "queued"
        assert result["queue_position"] == 1

    def test_fifo_order(self):
        q = CommandQueue()
        q._is_busy = True  # Prevent auto-processing

        q.enqueue(Command(type="next", payload={}))
        q.enqueue(Command(type="ask", payload={"target_name": "Maria"}))
        q.enqueue(Command(type="outro", payload={}))

        assert q.queue_size == 3

        # Process in order
        q._is_busy = False
        result = q.process_next()
        assert q.current_action.type == "next"

        q._is_busy = False
        result = q.process_next()
        assert q.current_action.type == "ask"

        q._is_busy = False
        result = q.process_next()
        assert q.current_action.type == "outro"

    def test_interrupt_bypasses_queue(self):
        q = CommandQueue()
        interrupt_received = []

        def on_interrupt(cmd):
            interrupt_received.append(cmd.type)
            return {"status": "interrupt", "command": cmd.type}

        q.set_callbacks(on_interrupt=on_interrupt)
        q._is_busy = True

        # Queue a normal command
        q.enqueue(Command(type="next", payload={}))

        # Send interrupt
        cmd = Command(type="pause", payload={}, priority=1)
        result = q.enqueue(cmd)

        assert result["status"] == "interrupt"
        assert "pause" in interrupt_received
        assert q.queue_size == 1  # Normal command still in queue

    def test_on_action_complete(self):
        q = CommandQueue()
        q._is_busy = True
        q._queue.append(Command(type="next", payload={}))

        result = q.on_action_complete()
        assert q.is_busy is True  # Now processing next
        assert q.current_action.type == "next"

    def test_on_action_complete_empty_queue(self):
        q = CommandQueue()
        q._is_busy = True

        result = q.on_action_complete()
        assert q.is_busy is False
        assert result["status"] == "idle"

    def test_clear(self):
        q = CommandQueue()
        q._is_busy = True
        q._queue.append(Command(type="next", payload={}))
        q._queue.append(Command(type="outro", payload={}))

        q.clear()
        assert q.queue_size == 0
        assert q.is_busy is False

    def test_get_status(self):
        q = CommandQueue()
        q._is_busy = True
        q._current_action = Command(type="presenting", payload={})
        q._queue.append(Command(type="next", payload={}))

        status = q.get_status()
        assert status["is_busy"] is True
        assert status["current_action"] == "presenting"
        assert status["queue_size"] == 1
        assert "next" in status["queued_commands"]

    def test_callback_on_command(self):
        q = CommandQueue()
        processed = []

        def on_command(cmd):
            processed.append(cmd.type)
            return {"status": "ok", "command": cmd.type}

        q.set_callbacks(on_command=on_command)
        q.enqueue(Command(type="intro", payload={}))

        assert "intro" in processed
