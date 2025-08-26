"""Tests for configuration module."""
import tempfile
from pathlib import Path

import pytest

from config import Config, get_pipeline_config


class TestConfig:
    """Test configuration management."""

    def test_validate_api_keys_all_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key validation when all keys are present."""
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_youtube_key")
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "test_genai_key")

        # Need to reload the config after setting env vars
        monkeypatch.setattr(Config, "YOUTUBE_API_KEY", "test_youtube_key")
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setattr(Config, "GOOGLE_GENAI_API_KEY", "test_genai_key")

        result = Config.validate_api_keys()

        assert result == {
            "youtube": True,
            "openai": True,
            "google_genai": True
        }

    def test_validate_api_keys_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key validation when keys are missing."""
        monkeypatch.setattr(Config, "YOUTUBE_API_KEY", "")
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "test_key")
        monkeypatch.setattr(Config, "GOOGLE_GENAI_API_KEY", "")

        result = Config.validate_api_keys()

        assert result == {
            "youtube": False,
            "openai": True,
            "google_genai": False
        }

    def test_get_missing_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting list of missing API keys."""
        monkeypatch.setattr(Config, "YOUTUBE_API_KEY", "")
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "test_key")
        monkeypatch.setattr(Config, "GOOGLE_GENAI_API_KEY", "")

        result = Config.get_missing_keys()

        assert set(result) == {"youtube", "google_genai"}

    def test_create_env_template(self) -> None:
        """Test creating environment template file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "test_template.env"

            Config.create_env_template(str(template_path))

            assert template_path.exists()
            content = template_path.read_text()
            assert "YOUTUBE_API_KEY=" in content
            assert "OPENAI_API_KEY=" in content
            assert "GOOGLE_GENAI_API_KEY=" in content


class TestPipelineConfig:
    """Test pipeline configuration creation."""

    def test_get_pipeline_config_defaults(self) -> None:
        """Test getting pipeline config with defaults."""
        config = get_pipeline_config()

        assert config.max_comments == 5000
        assert config.max_total_word_length == 80000
        assert config.openai_model == "gpt-4.5-preview"
        assert config.enable_transcript is True

    def test_get_pipeline_config_with_overrides(self) -> None:
        """Test getting pipeline config with overrides."""
        config = get_pipeline_config(
            max_comments=1000,
            openai_temperature=0.7,
            enable_transcript=False
        )

        assert config.max_comments == 1000
        assert config.openai_temperature == 0.7
        assert config.enable_transcript is False
        # Defaults should still be present
        assert config.max_total_word_length == 80000
