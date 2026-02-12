"""Tests for the audio pipeline — TTS service, manifest, and batch generation."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

# --- Kokoro batch generate tests ---

from tools.kokoro_batch_generate import collect_audio_jobs, export_text_files


SAMPLE_CONFIG = {
    "presentation": {
        "title": "Test Presentation",
        "total_slides": 3,
    },
    "slides": [
        {
            "id": 0,
            "title": "Title Slide",
            "narration": None,
            "audio_file": None,
            "has_interaction": False,
        },
        {
            "id": 1,
            "title": "Intro",
            "narration": "Hello everyone, welcome to the presentation.",
            "audio_file": "audio/slide_01_intro.mp3",
            "has_interaction": False,
        },
        {
            "id": 2,
            "title": "Main Content",
            "narration": "This is the main content of the slide.",
            "audio_file": "audio/slide_02_main.mp3",
            "has_interaction": True,
            "interaction": {
                "target": "Maria",
                "question": "What do you think about AI?",
                "question_audio": "audio/ask_02_maria.mp3",
            },
        },
    ],
}


class TestCollectAudioJobs:
    """Test audio job extraction from config."""

    def test_collects_narration_jobs(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        narration_jobs = [j for j in jobs if j["label"].endswith("_narration")]
        assert len(narration_jobs) == 2  # Slides 1 and 2 have narration

    def test_collects_interaction_jobs(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        ask_jobs = [j for j in jobs if j["label"].endswith("_ask")]
        assert len(ask_jobs) == 1  # Only slide 2 has interaction

    def test_skips_slides_without_narration(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        slide_ids = [j["slide_id"] for j in jobs]
        assert 0 not in slide_ids  # Title slide has no narration

    def test_slide_filter(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG, slide_filter=[1])
        assert len(jobs) == 1
        assert jobs[0]["slide_id"] == 1

    def test_slide_filter_with_interaction(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG, slide_filter=[2])
        assert len(jobs) == 2  # narration + interaction question

    def test_empty_filter_returns_nothing(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG, slide_filter=[99])
        assert len(jobs) == 0

    def test_job_structure(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        job = jobs[0]
        assert "slide_id" in job
        assert "title" in job
        assert "label" in job
        assert "text" in job
        assert "audio_filename" in job

    def test_text_is_stripped(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        for job in jobs:
            assert job["text"] == job["text"].strip()

    def test_audio_filename_is_basename(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        for job in jobs:
            assert "/" not in job["audio_filename"]
            assert "\\" not in job["audio_filename"]


class TestExportTextFiles:
    """Test text file export for manual Kokoro generation."""

    def test_creates_text_files(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        with tempfile.TemporaryDirectory() as tmpdir:
            export_text_files(jobs, Path(tmpdir))

            # Check that .txt files were created
            txt_files = list(Path(tmpdir).glob("*.txt"))
            # jobs count + README.txt
            assert len(txt_files) == len(jobs) + 1

    def test_text_content_matches(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        with tempfile.TemporaryDirectory() as tmpdir:
            export_text_files(jobs, Path(tmpdir))

            for job in jobs:
                txt_name = job["audio_filename"].replace(".mp3", ".txt")
                txt_path = Path(tmpdir) / txt_name
                assert txt_path.exists()
                content = txt_path.read_text(encoding="utf-8")
                assert content == job["text"]

    def test_creates_readme(self):
        jobs = collect_audio_jobs(SAMPLE_CONFIG)
        with tempfile.TemporaryDirectory() as tmpdir:
            export_text_files(jobs, Path(tmpdir))
            readme = Path(tmpdir) / "README.txt"
            assert readme.exists()
            content = readme.read_text(encoding="utf-8")
            assert "Kokoro TTS" in content


# --- Audio manifest tests ---

from tools.audio_manifest import get_expected_files, get_audio_file_info


class TestGetExpectedFiles:
    """Test expected file extraction from config."""

    def test_extracts_narration_files(self):
        expected = get_expected_files(SAMPLE_CONFIG)
        narration = [e for e in expected if e["type"] == "narration"]
        assert len(narration) == 2

    def test_extracts_interaction_files(self):
        expected = get_expected_files(SAMPLE_CONFIG)
        interaction = [e for e in expected if e["type"] == "interaction"]
        assert len(interaction) == 1

    def test_file_structure(self):
        expected = get_expected_files(SAMPLE_CONFIG)
        for item in expected:
            assert "filename" in item
            assert "slide_id" in item
            assert "title" in item
            assert "type" in item
            assert "text_chars" in item

    def test_text_chars_count(self):
        expected = get_expected_files(SAMPLE_CONFIG)
        intro = [e for e in expected if e["slide_id"] == 1 and e["type"] == "narration"][0]
        assert intro["text_chars"] == len("Hello everyone, welcome to the presentation.")


# --- TTS service tests (mocked) ---

class TestTTSService:
    """Test TTS service functions with mocked HTTP calls."""

    def test_synthesize_speech_success(self):
        async def _run():
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"fake_audio_bytes"
            mock_response.raise_for_status = MagicMock()

            with patch("backend.services.tts_service._get_api_key", return_value="test_key"), \
                 patch("backend.services.tts_service._get_voice_id", return_value="test_voice"), \
                 patch("httpx.AsyncClient") as mock_client_cls:

                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                from backend.services.tts_service import synthesize_speech
                result = await synthesize_speech("Hello world")

                assert result == b"fake_audio_bytes"
                mock_client.post.assert_called_once()

        asyncio.run(_run())

    def test_synthesize_speech_saves_to_file(self):
        async def _run():
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"fake_audio_bytes"
            mock_response.raise_for_status = MagicMock()

            with patch("backend.services.tts_service._get_api_key", return_value="test_key"), \
                 patch("backend.services.tts_service._get_voice_id", return_value="test_voice"), \
                 patch("httpx.AsyncClient") as mock_client_cls:

                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                from backend.services.tts_service import synthesize_speech

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    output_path = f.name

                try:
                    await synthesize_speech("Hello world", output_path=output_path)
                    assert Path(output_path).exists()
                    assert Path(output_path).read_bytes() == b"fake_audio_bytes"
                finally:
                    os.unlink(output_path)

        asyncio.run(_run())

    def test_is_configured_true(self):
        with patch.dict(os.environ, {
            "ELEVENLABS_API_KEY": "test_key",
            "ELEVENLABS_VOICE_ID": "test_voice",
        }):
            from backend.services.tts_service import is_configured
            assert is_configured() is True

    def test_is_configured_false(self):
        env = os.environ.copy()
        env.pop("ELEVENLABS_API_KEY", None)
        env.pop("ELEVENLABS_VOICE_ID", None)
        with patch.dict(os.environ, env, clear=True):
            from backend.services.tts_service import is_configured
            assert is_configured() is False


class TestTTSStreamBase64:
    """Test the base64 streaming wrapper."""

    def test_stream_yields_chunks_and_final(self):
        async def _run():
            async def mock_stream(*args, **kwargs):
                yield b"chunk1"
                yield b"chunk2"

            with patch("backend.services.tts_service.stream_speech", side_effect=mock_stream):
                from backend.services.tts_service import stream_speech_as_base64

                chunks = []
                async for msg in stream_speech_as_base64("test"):
                    chunks.append(msg)

                # 2 data chunks + 1 final marker
                assert len(chunks) == 3
                assert chunks[0]["type"] == "audio_chunk"
                assert chunks[0]["data"]["index"] == 0
                assert chunks[0]["data"]["final"] is False
                assert chunks[1]["data"]["index"] == 1
                assert chunks[2]["data"]["final"] is True
                assert chunks[2]["data"]["chunk"] == ""

        asyncio.run(_run())
