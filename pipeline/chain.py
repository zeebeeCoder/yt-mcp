from datetime import datetime
from typing import Optional

from models.schemas import (
    AnalysisResult,
    PipelineConfig,
    ProcessingContext,
    ProcessingStep,
    TranscriptData,
    VideoMetadata,
)
from pipeline.evaluators import CriticalThinkingEvaluator
from pipeline.extractors import YouTubeExtractor
from pipeline.processors import OpenAIProcessor, PromptTemplates
from pipeline.synthesizers import ContentSynthesizer
from utils.errors import PipelineError
from utils.logging import StepLogger, get_logger

logger = get_logger(__name__)


class ChainProcessor:
    """
    Main chain-of-thought processor that orchestrates the 5-step analysis pipeline:
    1. Extract - Get YouTube data (metadata, transcript, comments)
    2. Process - Generate AI summaries of transcript and comments
    3. Synthesize - Compress and combine insights
    4. Evaluate - Apply critical thinking standards
    5. Prioritize - Select most impactful follow-up questions
    """

    def __init__(self, youtube_api_key: str, openai_api_key: str, google_genai_api_key: str):
        self.youtube_extractor = YouTubeExtractor(youtube_api_key)
        self.openai_processor = OpenAIProcessor(openai_api_key)
        self.content_synthesizer = ContentSynthesizer(google_genai_api_key)
        self.critical_evaluator = CriticalThinkingEvaluator(google_genai_api_key)

        self.step_logger = StepLogger(logger)

    def analyze_video(
        self, video_url: str, config: Optional[PipelineConfig] = None, instruction: str = None
    ) -> AnalysisResult:
        """
        Run the complete chain-of-thought analysis on a YouTube video

        Args:
            video_url: YouTube video URL
            config: Pipeline configuration (uses defaults if None)
            instruction: Custom instruction for transcript analysis

        Returns:
            Complete analysis result with all processing steps
        """

        if config is None:
            config = PipelineConfig()

        if instruction is None:
            instruction = PromptTemplates.SUMMARIZE_FOR_REFLECTION

        start_time = datetime.now()
        logger.info(f"Starting chain-of-thought analysis for: {video_url}")

        try:
            # Initialize processing context
            video_id = self.youtube_extractor.extract_video_id(video_url)
            metadata = self._step_1_extract_metadata(video_id)

            context = ProcessingContext(video_metadata=metadata, config=config)

            # Step 1: Extract YouTube data
            self._step_1_extract_data(context)

            # Step 2: Process with AI
            self._step_2_process_content(context, instruction)

            # Step 3: Synthesize insights
            self._step_3_synthesize_content(context)

            # Step 4: Evaluate with critical thinking
            self._step_4_evaluate_content(context)

            # Step 5: Prioritize questions (handled in step 4)

            # Create final result
            total_time = (datetime.now() - start_time).total_seconds()

            result = AnalysisResult(
                video_metadata=context.video_metadata,
                transcript=context.transcript,
                comments=context.comments,
                processing_steps=context.processing_steps,
                transcript_summary=context.transcript_summary,
                comments_summary=context.comments_summary,
                compressed_summary=context.compressed_summary,
                critical_assessment=context.critical_assessment,
                total_processing_time=total_time,
            )

            logger.info(f"Analysis completed in {total_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise PipelineError(f"Analysis pipeline failed: {e}") from e

    def _step_1_extract_metadata(self, video_id: str) -> VideoMetadata:
        """Extract video metadata as prerequisite"""
        self.step_logger.start_step("Extract Video Metadata")

        try:
            metadata = self.youtube_extractor.fetch_video_metadata(video_id)
            self.step_logger.end_step(success=True)
            return metadata

        except Exception as e:
            self.step_logger.end_step(success=False, error_message=str(e))
            raise

    def _step_1_extract_data(self, context: ProcessingContext) -> None:
        """Step 1: Extract YouTube data (transcript and comments)"""

        # Extract transcript
        if context.config.enable_transcript:
            self.step_logger.start_step("Extract Video Transcript")

            try:
                context.transcript = self.youtube_extractor.fetch_transcript(
                    context.video_metadata.video_id
                )

                duration = self.step_logger.end_step(success=True)
                context.processing_steps.append(
                    ProcessingStep(
                        step_name="extract_transcript",
                        input_data=context.video_metadata.video_id,
                        output_data=f"Transcript available: {context.transcript.available}, Words: {context.transcript.word_count}",
                        processing_time=duration,
                        success=True,
                    )
                )

            except Exception as e:
                duration = self.step_logger.end_step(success=False, error_message=str(e))
                context.processing_steps.append(
                    ProcessingStep(
                        step_name="extract_transcript",
                        input_data=context.video_metadata.video_id,
                        output_data="",
                        processing_time=duration,
                        success=False,
                        error_message=str(e),
                    )
                )
                # Don't fail the entire pipeline for transcript issues
                context.transcript = TranscriptData(text=None, word_count=0, available=False)

        # Extract comments
        if context.config.enable_comments:
            self.step_logger.start_step("Extract Video Comments")

            try:
                context.comments = self.youtube_extractor.fetch_comments(
                    context.video_metadata.video_id,
                    context.config.max_comments,
                    context.config.max_total_word_length,
                )

                duration = self.step_logger.end_step(success=True)
                context.processing_steps.append(
                    ProcessingStep(
                        step_name="extract_comments",
                        input_data=context.video_metadata.video_id,
                        output_data=f"Comments: {context.comments.total_count}, Words: {context.comments.total_word_count}",
                        processing_time=duration,
                        success=True,
                    )
                )

            except Exception as e:
                duration = self.step_logger.end_step(success=False, error_message=str(e))
                context.processing_steps.append(
                    ProcessingStep(
                        step_name="extract_comments",
                        input_data=context.video_metadata.video_id,
                        output_data="",
                        processing_time=duration,
                        success=False,
                        error_message=str(e),
                    )
                )
                # Don't fail the entire pipeline for comments issues
                from models.schemas import CommentsData

                context.comments = CommentsData(
                    comments=[], total_count=0, processed_count=0, total_word_count=0
                )
        else:
            # Comments disabled - create empty comments data
            from models.schemas import CommentsData

            context.comments = CommentsData(
                comments=[], total_count=0, processed_count=0, total_word_count=0
            )

    def _step_2_process_content(self, context: ProcessingContext, instruction: str) -> None:
        """Step 2: Process content with AI (transcript and comments summaries)"""

        # Process transcript if available and enabled
        if (
            context.config.enable_transcript_processing
            and context.transcript
            and context.transcript.available
        ):
            self.step_logger.start_step("Process Video Transcript")

            try:
                transcript_chunks = []
                for chunk in self.openai_processor.generate_transcript_summary(
                    context.transcript, instruction, context.config
                ):
                    transcript_chunks.append(chunk)

                context.transcript_summary = "".join(transcript_chunks)
                duration = self.step_logger.end_step(success=True)

                context.processing_steps.append(
                    ProcessingStep(
                        step_name="process_transcript",
                        input_data=f"Transcript ({context.transcript.word_count} words)",
                        output_data=f"Summary ({len(context.transcript_summary.split())} words)",
                        processing_time=duration,
                        success=True,
                    )
                )

            except Exception as e:
                duration = self.step_logger.end_step(success=False, error_message=str(e))
                context.processing_steps.append(
                    ProcessingStep(
                        step_name="process_transcript",
                        input_data=f"Transcript ({context.transcript.word_count} words)",
                        output_data="",
                        processing_time=duration,
                        success=False,
                        error_message=str(e),
                    )
                )
                # Continue without transcript summary

        # Process comments if enabled and available
        if (
            context.config.enable_comments_processing
            and context.comments
            and context.comments.total_count > 0
        ):
            self.step_logger.start_step("Process Video Comments")

            try:
                comments_chunks = []
                for chunk in self.openai_processor.generate_comments_summary(
                    context.comments, context.config
                ):
                    comments_chunks.append(chunk)

                context.comments_summary = "".join(comments_chunks)
                duration = self.step_logger.end_step(success=True)

                context.processing_steps.append(
                    ProcessingStep(
                        step_name="process_comments",
                        input_data=f"Comments ({context.comments.total_count} items)",
                        output_data=f"Summary ({len(context.comments_summary.split())} words)",
                        processing_time=duration,
                        success=True,
                    )
                )

            except Exception as e:
                duration = self.step_logger.end_step(success=False, error_message=str(e))
                context.processing_steps.append(
                    ProcessingStep(
                        step_name="process_comments",
                        input_data=f"Comments ({context.comments.total_count} items)",
                        output_data="",
                        processing_time=duration,
                        success=False,
                        error_message=str(e),
                    )
                )
                # Don't fail the entire pipeline for comments processing issues
                context.comments_summary = ""

    def _step_3_synthesize_content(self, context: ProcessingContext) -> None:
        """Step 3: Synthesize and compress insights"""

        if not context.config.enable_synthesis:
            # Use the best available summary when synthesis is disabled
            if context.comments_summary:
                context.compressed_summary = context.comments_summary
            elif context.transcript_summary:
                context.compressed_summary = context.transcript_summary
            else:
                context.compressed_summary = "Analysis completed without content synthesis."
            return

        self.step_logger.start_step("Synthesize Content")

        try:
            context.compressed_summary = self.content_synthesizer.compress_content(
                context.transcript_summary or "", context.comments_summary or "", context.config
            )

            duration = self.step_logger.end_step(success=True)
            context.processing_steps.append(
                ProcessingStep(
                    step_name="synthesize_content",
                    input_data="Transcript + Comments summaries",
                    output_data=f"Compressed summary ({len(context.compressed_summary.split())} words)",
                    processing_time=duration,
                    success=True,
                )
            )

        except Exception as e:
            duration = self.step_logger.end_step(success=False, error_message=str(e))
            context.processing_steps.append(
                ProcessingStep(
                    step_name="synthesize_content",
                    input_data="Transcript + Comments summaries",
                    output_data="",
                    processing_time=duration,
                    success=False,
                    error_message=str(e),
                )
            )
            raise

    def _step_4_evaluate_content(self, context: ProcessingContext) -> None:
        """Step 4: Evaluate with critical thinking standards"""

        if not context.config.enable_evaluation:
            # Create minimal assessment to avoid breaking downstream code
            from models.schemas import CriticalThinkingAssessment

            context.critical_assessment = CriticalThinkingAssessment(
                standards=[], selected_questions=[], impact_scores={}
            )
            return

        self.step_logger.start_step("Evaluate Critical Thinking")

        try:
            context.critical_assessment = self.critical_evaluator.evaluate_content(
                context.transcript_summary or "", context.comments_summary or "", context.config
            )

            duration = self.step_logger.end_step(success=True)
            context.processing_steps.append(
                ProcessingStep(
                    step_name="evaluate_critical_thinking",
                    input_data="Transcript + Comments summaries",
                    output_data=f"Assessment with {len(context.critical_assessment.standards)} standards, {len(context.critical_assessment.selected_questions)} priority questions",
                    processing_time=duration,
                    success=True,
                )
            )

        except Exception as e:
            duration = self.step_logger.end_step(success=False, error_message=str(e))
            context.processing_steps.append(
                ProcessingStep(
                    step_name="evaluate_critical_thinking",
                    input_data="Transcript + Comments summaries",
                    output_data="",
                    processing_time=duration,
                    success=False,
                    error_message=str(e),
                )
            )
            raise
