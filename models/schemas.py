from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class VideoMetadata(BaseModel):
    """Video metadata from YouTube API"""

    video_id: str
    title: str
    author: str
    channel_title: str
    published_date: datetime
    url: HttpUrl


class Comment(BaseModel):
    """Individual YouTube comment"""

    comment: str
    user_name: str
    date: datetime
    like_count: int
    replies: list[str] = Field(default_factory=list)


class CommentsData(BaseModel):
    """Collection of video comments"""

    comments: list[Comment]
    total_count: int
    processed_count: int
    total_word_count: int


class TranscriptData(BaseModel):
    """Video transcript data"""

    text: Optional[str]
    word_count: int
    available: bool
    language: Optional[str] = None
    error_message: Optional[str] = None


class ProcessingStep(BaseModel):
    """Individual processing step result"""

    step_name: str
    input_data: str
    output_data: str
    processing_time: float
    success: bool
    error_message: Optional[str] = None


class CriticalThinkingStandard(BaseModel):
    """Critical thinking evaluation standard"""

    name: str
    evaluation: str
    rating: int = Field(ge=0, le=10)
    followup_questions: list[str]


class CriticalThinkingAssessment(BaseModel):
    """Complete critical thinking assessment"""

    standards: list[CriticalThinkingStandard]
    selected_questions: list[str]
    impact_scores: dict[str, float]


class AnalysisResult(BaseModel):
    """Final analysis result from the chain-of-thought pipeline"""

    video_metadata: VideoMetadata
    transcript: Optional[TranscriptData]
    comments: CommentsData
    processing_steps: list[ProcessingStep]
    transcript_summary: Optional[str] = None
    comments_summary: Optional[str] = None
    compressed_summary: Optional[str] = None
    critical_assessment: CriticalThinkingAssessment
    total_processing_time: float


class PipelineConfig(BaseModel):
    """Configuration for the analysis pipeline"""

    max_comments: int = 5000
    max_total_word_length: int = 80000
    openai_model: str = "gpt-5"  # GPT-5 with enhanced reasoning and Responses API
    openai_temperature: float = 0.35
    gemini_model: str = "gemini-1.5-flash"
    gemini_temperature: float = 0.5
    num_selected_questions: int = 6

    # Step toggles - fine-grained control over pipeline execution
    enable_transcript: bool = True
    enable_comments: bool = True
    enable_transcript_processing: bool = True
    enable_comments_processing: bool = True
    enable_synthesis: bool = True
    enable_evaluation: bool = True

    # Legacy/future features
    enable_audio_download: bool = False


class ProcessingContext(BaseModel):
    """Context passed between processing steps"""

    video_metadata: VideoMetadata
    transcript: Optional[TranscriptData] = None
    comments: Optional[CommentsData] = None
    transcript_summary: Optional[str] = None
    comments_summary: Optional[str] = None
    compressed_summary: Optional[str] = None
    critical_assessment: Optional[CriticalThinkingAssessment] = None
    processing_steps: list[ProcessingStep] = Field(default_factory=list)
    config: PipelineConfig
