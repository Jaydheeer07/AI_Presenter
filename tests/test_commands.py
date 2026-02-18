"""Tests for slash command parsing."""

import pytest

from backend.agent.commands import Command, parse_command, VALID_COMMANDS


class TestParseCommand:
    """Test the parse_command function."""

    def test_simple_commands(self):
        """Test parsing of simple slash commands without arguments."""
        for cmd in [
            "intro", "start", "next", "prev", "qa", "outro", "pause",
            "resume", "skip", "status", "example", "video", "audio",
        ]:
            result = parse_command(f"/{cmd}")
            assert result.type == cmd, f"Failed for /{cmd}"

    def test_goto_valid(self):
        result = parse_command("/goto 5")
        assert result.type == "goto"
        assert result.payload["slide_number"] == 5

    def test_goto_invalid(self):
        result = parse_command("/goto abc")
        assert result.type == "error"
        assert "slide number" in result.payload["error"].lower()

    def test_ask_valid(self):
        result = parse_command("/ask Maria: What AI tools do you use daily?")
        assert result.type == "ask"
        assert result.payload["target_name"] == "Maria"
        assert result.payload["question"] == "What AI tools do you use daily?"

    def test_ask_name_only(self):
        result = parse_command("/ask Maria")
        assert result.type == "ask"
        assert result.payload["target_name"] == "Maria"
        assert result.payload["question"] == ""

    def test_ask_invalid_format(self):
        result = parse_command("/ask")
        assert result.type == "error"
        assert "Format" in result.payload["error"]

    def test_pick_valid(self):
        result = parse_command("/pick 3")
        assert result.type == "pick"
        assert result.payload["question_id"] == 3

    def test_pick_invalid(self):
        result = parse_command("/pick abc")
        assert result.type == "error"

    def test_free_text_answer(self):
        result = parse_command("Maria says she uses ChatGPT for emails")
        assert result.type == "answer"
        assert result.payload["summary"] == "Maria says she uses ChatGPT for emails"

    def test_unknown_command(self):
        result = parse_command("/foobar")
        assert result.type == "unknown"

    def test_interrupt_priority(self):
        result = parse_command("/pause")
        assert result.priority == 1

        result = parse_command("/next")
        assert result.priority == 0

    def test_whitespace_handling(self):
        result = parse_command("  /next  ")
        assert result.type == "next"

    def test_empty_input(self):
        result = parse_command("")
        assert result.type == "answer"
        assert result.payload["summary"] == ""

    def test_case_insensitive(self):
        result = parse_command("/NEXT")
        assert result.type == "next"

    def test_ask_preserves_question(self):
        result = parse_command("/ask Jake: Have you automated any part of your workflow?")
        assert result.payload["target_name"] == "Jake"
        assert "automated" in result.payload["question"]
