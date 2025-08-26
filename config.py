import os
from typing import Any, Optional

from dotenv import load_dotenv

from models.schemas import PipelineConfig

load_dotenv()


class Config:
    """Application configuration management"""

    # API Keys
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_GENAI_API_KEY: str = os.getenv("GOOGLE_GENAI_API_KEY", "")

    # Pipeline Configuration
    DEFAULT_PIPELINE_CONFIG = PipelineConfig()

    @classmethod
    def validate_api_keys(cls) -> dict[str, bool]:
        """Validate that required API keys are present"""
        return {
            "youtube": bool(cls.YOUTUBE_API_KEY),
            "openai": bool(cls.OPENAI_API_KEY),
            "google_genai": bool(cls.GOOGLE_GENAI_API_KEY)
        }

    @classmethod
    def get_missing_keys(cls) -> list[str]:
        """Get list of missing API keys"""
        validation = cls.validate_api_keys()
        return [key for key, valid in validation.items() if not valid]

    @classmethod
    def create_env_template(cls, file_path: str = ".env.template") -> None:
        """Create a template .env file"""
        template_content = """# YouTube Data API v3 key
YOUTUBE_API_KEY=your_youtube_api_key_here

# OpenAI API key  
OPENAI_API_KEY=your_openai_api_key_here

# Google GenAI (Gemini) API key
GOOGLE_GENAI_API_KEY=your_google_genai_api_key_here
"""
        with open(file_path, "w") as f:
            f.write(template_content)


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
    enable_audio_download: Optional[bool] = None
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
