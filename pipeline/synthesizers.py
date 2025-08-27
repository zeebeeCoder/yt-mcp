from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from models.schemas import PipelineConfig
from utils.errors import APIError
from utils.logging import get_logger

logger = get_logger(__name__)


class ContentSynthesizer:
    """Google GenAI client for content synthesis and compression"""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

        self.compression_prompt_template = """
Extract maximum value through rigorous intellectual processing before communicating. Identify essential concepts by first thinking deeply about what would save the recipient cognitive effort.

Process:

- Analyze for conceptual redundancies and merge related ideas
- Structure content in problem-to-solution narrative arc
- Eliminate clichés and repetitive phrasing
- Discard information that doesn't contribute meaningful depth

Deliver either:

1. One concentrated paragraph capturing essential meaning, or
2. Minimal bullet points preserving only vital information

Include a 3-10 word headline using primarily nouns that encapsulates the core concept.

Remember: The value lies not in what you include, but in what you've thoughtfully eliminated through deep analysis.


Here is the input text / information:

=== 
Summary of the topic or assumptions made by the speaker:

{transcript_summary}

=== Summary of community people comments on the topic:

{comments_summary}
"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def compress_content(
        self, transcript_summary: str, comments_summary: str, config: PipelineConfig
    ) -> str:
        """Compress and synthesize transcript and comments summaries"""

        # Calculate input metrics
        input_chars = len((transcript_summary or "") + (comments_summary or ""))
        input_words = len((transcript_summary or "").split()) + len(
            (comments_summary or "").split()
        )
        estimated_input_tokens = input_chars // 4

        logger.info(f"Compressing content using {config.gemini_model}")
        logger.info("Synthesis input metrics:")
        logger.info(f"  - Combined characters: {input_chars:,}")
        logger.info(f"  - Combined words: {input_words:,}")
        logger.info(f"  - Estimated tokens: {estimated_input_tokens:,}")

        prompt = self.compression_prompt_template.format(
            transcript_summary=transcript_summary or "No transcript summary available.",
            comments_summary=comments_summary,
        )

        prompt_chars = len(prompt)
        estimated_prompt_tokens = prompt_chars // 4
        logger.info("Gemini prompt metrics:")
        logger.info(f"  - Total prompt characters: {prompt_chars:,}")
        logger.info(f"  - Estimated prompt tokens: {estimated_prompt_tokens:,}")

        generation_config = types.GenerateContentConfig(
            temperature=config.gemini_temperature,
        )

        try:
            import time

            start_time = time.time()

            logger.info("Gemini API call starting:")
            logger.info(f"  - Model: {config.gemini_model}")
            logger.info(f"  - Temperature: {config.gemini_temperature}")

            response = self.client.models.generate_content(
                model=config.gemini_model,
                contents=prompt,
                config=generation_config,
            )

            # Calculate latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Log output metrics
            output_chars = len(response.text)
            output_words = len(response.text.split())
            estimated_output_tokens = output_chars // 4
            compression_ratio = (input_chars / output_chars) if output_chars > 0 else 0

            logger.info("Gemini API call completed:")
            logger.info(f"  - Latency: {latency_ms:.0f}ms")
            logger.info(f"  - Output characters: {output_chars:,}")
            logger.info(f"  - Output words: {output_words:,}")
            logger.info(f"  - Estimated output tokens: {estimated_output_tokens:,}")
            logger.info(f"  - Compression ratio: {compression_ratio:.1f}:1")

            # Check if usage stats are available in response
            if hasattr(response, "usage") and response.usage:
                logger.info("Gemini token usage (actual):")
                logger.info(f"  - Input tokens: {getattr(response.usage, 'input_tokens', 'N/A'):,}")
                logger.info(
                    f"  - Output tokens: {getattr(response.usage, 'output_tokens', 'N/A'):,}"
                )
                logger.info(f"  - Total tokens: {getattr(response.usage, 'total_tokens', 'N/A'):,}")
            else:
                logger.warning("Token usage data not available from Gemini response")

            logger.info("Content compression completed successfully")
            return response.text

        except Exception as e:
            logger.error(f"Google GenAI error during content compression: {e}")
            raise APIError(f"Content compression failed: {e}", "google_genai")


class InsightExtractor:
    """Extract key insights and create structured summaries"""

    @staticmethod
    def extract_headline(compressed_content: str) -> Optional[str]:
        """Extract headline from compressed content if present"""
        lines = compressed_content.strip().split("\n")

        # Look for markdown-style headline
        for line in lines:
            line = line.strip()
            if line.startswith("**") and line.endswith("**"):
                return line.strip("*").strip()
            elif line.startswith("#"):
                return line.lstrip("#").strip()

        # If no headline found, take first line if it's short enough
        first_line = lines[0].strip() if lines else ""
        if len(first_line) <= 50 and first_line:
            return first_line

        return None

    @staticmethod
    def extract_key_points(compressed_content: str) -> list[str]:
        """Extract bullet points or key insights from content"""
        lines = compressed_content.strip().split("\n")
        key_points = []

        for line in lines:
            line = line.strip()
            # Look for bullet points or numbered items
            if line.startswith(("- ", "* ", "• ")):
                key_points.append(line[2:].strip())
            elif line.startswith(tuple(f"{i}. " for i in range(1, 10))):
                # Remove number prefix
                key_points.append(line.split(". ", 1)[1] if ". " in line else line)

        return key_points

    @classmethod
    def analyze_content_structure(cls, compressed_content: str) -> dict:
        """Analyze the structure of compressed content"""
        headline = cls.extract_headline(compressed_content)
        key_points = cls.extract_key_points(compressed_content)

        # Calculate content metrics
        word_count = len(compressed_content.split())
        char_count = len(compressed_content)

        return {
            "headline": headline,
            "key_points": key_points,
            "word_count": word_count,
            "char_count": char_count,
            "has_structure": bool(headline or key_points),
            "compression_ratio": None,  # Will be calculated when we have original length
        }
