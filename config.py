import os
from typing import Any, Optional

from models.schemas import PipelineConfig
from utils.credentials import get_missing_keys, load_credentials, validate_api_keys


class Config:
    """Application configuration management"""

    @classmethod
    def load_config(cls, env_file: Optional[str] = None, config_dir: Optional[str] = None) -> None:
        """Load configuration from specified sources"""
        load_credentials(env_file, config_dir)

    @classmethod
    def get_api_keys(cls) -> dict[str, str]:
        """Get current API keys from environment"""
        return {
            "youtube": os.getenv("YOUTUBE_API_KEY", ""),
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "google_genai": os.getenv("GOOGLE_GENAI_API_KEY", ""),
        }

    # API Keys (dynamic properties)
    @property
    def YOUTUBE_API_KEY(self) -> str:
        return os.getenv("YOUTUBE_API_KEY", "")

    @property
    def OPENAI_API_KEY(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def GOOGLE_GENAI_API_KEY(self) -> str:
        return os.getenv("GOOGLE_GENAI_API_KEY", "")

    # Class-level access for backward compatibility
    @classmethod
    def validate_api_keys(cls) -> dict[str, bool]:
        """Validate that required API keys are present"""
        return validate_api_keys()

    @classmethod
    def get_missing_keys(cls) -> list[str]:
        """Get list of missing API keys"""
        return get_missing_keys()

    # Pipeline Configuration
    DEFAULT_PIPELINE_CONFIG = PipelineConfig()


# Create singleton instance
config = Config()


def get_pipeline_config(
    max_comments: Optional[int] = None,
    max_total_word_length: Optional[int] = None,
    openai_model: Optional[str] = None,
    openai_temperature: Optional[float] = None,
    gemini_model: Optional[str] = None,
    gemini_temperature: Optional[float] = None,
    num_selected_questions: Optional[int] = None,
    # Step control options
    enable_transcript: Optional[bool] = None,
    enable_comments: Optional[bool] = None,
    enable_transcript_processing: Optional[bool] = None,
    enable_comments_processing: Optional[bool] = None,
    enable_synthesis: Optional[bool] = None,
    enable_evaluation: Optional[bool] = None,
    enable_audio_download: Optional[bool] = None,
) -> PipelineConfig:
    """Create pipeline configuration with optional overrides"""
    config_dict: dict[str, Any] = {}

    if max_comments is not None:
        config_dict["max_comments"] = max_comments
    if max_total_word_length is not None:
        config_dict["max_total_word_length"] = max_total_word_length
    if openai_model is not None:
        config_dict["openai_model"] = openai_model
    if openai_temperature is not None:
        config_dict["openai_temperature"] = openai_temperature
    if gemini_model is not None:
        config_dict["gemini_model"] = gemini_model
    if gemini_temperature is not None:
        config_dict["gemini_temperature"] = gemini_temperature
    if num_selected_questions is not None:
        config_dict["num_selected_questions"] = num_selected_questions

    # Step control options
    if enable_transcript is not None:
        config_dict["enable_transcript"] = enable_transcript
    if enable_comments is not None:
        config_dict["enable_comments"] = enable_comments
    if enable_transcript_processing is not None:
        config_dict["enable_transcript_processing"] = enable_transcript_processing
    if enable_comments_processing is not None:
        config_dict["enable_comments_processing"] = enable_comments_processing
    if enable_synthesis is not None:
        config_dict["enable_synthesis"] = enable_synthesis
    if enable_evaluation is not None:
        config_dict["enable_evaluation"] = enable_evaluation
    if enable_audio_download is not None:
        config_dict["enable_audio_download"] = enable_audio_download

    # Start with defaults and override with provided values
    return PipelineConfig(**config_dict)
