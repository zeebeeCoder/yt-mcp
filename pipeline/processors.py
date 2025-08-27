from collections.abc import Iterator

import pandas as pd
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from models.schemas import CommentsData, PipelineConfig, TranscriptData
from utils.errors import APIError
from utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIProcessor:
    """OpenAI API client for content analysis"""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = (
            "You are a creative philosopher technologist. You understand process, people and tools and techniques. "
            "Focus on communication style, Identify and Reduce Redundancy, Focus on Novelty and Relevance. "
            "Structure Communication, Organize content logically."
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_transcript_summary(
        self, transcript: TranscriptData, instruction: str, config: PipelineConfig
    ) -> Iterator[str]:
        """Generate streaming summary of video transcript"""

        if not transcript.available or not transcript.text:
            logger.warning("No transcript available for summarization")
            yield "No transcript available for analysis."
            return

        # Calculate input metrics
        input_chars = len(transcript.text)
        input_words = len(transcript.text.split())
        estimated_input_tokens = input_chars // 4

        logger.info(f"Generating transcript summary using {config.openai_model}")
        logger.info("Input transcript metrics:")
        logger.info(f"  - Characters: {input_chars:,}")
        logger.info(f"  - Words: {input_words:,}")
        logger.info(f"  - Estimated tokens: {estimated_input_tokens:,}")

        # GPT-5 has increased context window
        MAX_CONTEXT_TOKENS = 200000  # GPT-5 increased context window
        RESERVED_TOKENS = 80000  # For prompt template and response (conservative)
        MAX_INPUT_TOKENS = MAX_CONTEXT_TOKENS - RESERVED_TOKENS  # 120,000 tokens

        transcript_text = transcript.text
        if estimated_input_tokens > MAX_INPUT_TOKENS:
            logger.warning(
                f"Transcript too long ({estimated_input_tokens:,} tokens), truncating to {MAX_INPUT_TOKENS:,} tokens"
            )
            # Truncate to approximately MAX_INPUT_TOKENS
            max_chars = MAX_INPUT_TOKENS * 4  # Rough estimate: 1 token ≈ 4 chars
            transcript_text = transcript.text[:max_chars]

            # Recalculate metrics
            input_chars = len(transcript_text)
            input_words = len(transcript_text.split())
            estimated_input_tokens = input_chars // 4
            logger.info("Truncated transcript metrics:")
            logger.info(f"  - Characters: {input_chars:,}")
            logger.info(f"  - Words: {input_words:,}")
            logger.info(f"  - Estimated tokens: {estimated_input_tokens:,}")

        # Use the enhanced SUMMARIZE_FOR_REFLECTION template with custom instruction
        base_prompt = PromptTemplates.SUMMARIZE_FOR_REFLECTION
        if (
            instruction.strip()
            != "Summarize the video content, extracting the core facts and main message."
        ):
            # If custom instruction provided, append it as additional context
            analysis_prompt = f"{base_prompt}\n\nAdditional Context/Focus: {instruction}"
        else:
            analysis_prompt = base_prompt

        # For GPT-5, combine system prompt and user prompt for the responses API
        full_prompt = f"{self.system_prompt}\n\n{analysis_prompt}\n\nTranscript to analyze:\n\n{transcript_text}\n\n"

        prompt_chars = len(full_prompt)
        estimated_prompt_tokens = prompt_chars // 4
        logger.info("Full prompt metrics:")
        logger.info(f"  - Total prompt characters: {prompt_chars:,}")
        logger.info(f"  - Estimated prompt tokens: {estimated_prompt_tokens:,}")

        try:
            import time

            start_time = time.time()

            logger.info("GPT-5 Responses API call starting:")
            logger.info(f"  - Model: {config.openai_model}")
            logger.info(f"  - Temperature: {config.openai_temperature}")
            logger.info("  - Reasoning Effort: medium (for comprehensive analysis)")

            # Use GPT-5 Responses API for enhanced capabilities
            if config.openai_model == "gpt-5":
                response = self.client.responses.create(
                    model=config.openai_model,
                    input=full_prompt,
                    reasoning={"effort": "medium"},  # Medium effort for balanced analysis
                    # Note: GPT-5 Responses API doesn't support temperature parameter
                )

                # GPT-5 responses API doesn't support streaming, so yield the full response
                output_content = response.output_text
                yield output_content

            else:
                # Fallback to chat completions for other models
                stream = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {
                            "role": "user",
                            "content": f"{analysis_prompt}\n\nTranscript to analyze:\n\n{transcript_text}\n\n",
                        },
                    ],
                    temperature=config.openai_temperature,
                    model=config.openai_model,
                    stream=True,
                    stream_options={"include_usage": True},  # Get token usage with streaming
                )

                output_content = ""
                usage_data = None

                for chunk in stream:
                    if (
                        chunk.choices
                        and len(chunk.choices) > 0
                        and chunk.choices[0].delta.content is not None
                    ):
                        content = chunk.choices[0].delta.content
                        output_content += content
                        yield content

                    # Capture usage data from the final chunk
                    if hasattr(chunk, "usage") and chunk.usage is not None:
                        usage_data = chunk.usage

            # Calculate latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Log output metrics
            output_chars = len(output_content)
            output_words = len(output_content.split())
            estimated_output_tokens = output_chars // 4
            compression_ratio = (input_chars / output_chars) if output_chars > 0 else 0

            if config.openai_model == "gpt-5":
                logger.info("GPT-5 Responses API call completed:")
            else:
                logger.info("OpenAI API call completed:")
            logger.info(f"  - Latency: {latency_ms:.0f}ms")
            logger.info(f"  - Output characters: {output_chars:,}")
            logger.info(f"  - Output words: {output_words:,}")
            logger.info(f"  - Estimated output tokens: {estimated_output_tokens:,}")
            logger.info(f"  - Compression ratio: {compression_ratio:.1f}:1")

            # Log actual token usage if available (for non-GPT-5 models)
            if config.openai_model != "gpt-5" and usage_data:
                logger.info("OpenAI token usage (actual):")
                logger.info(f"  - Prompt tokens: {usage_data.prompt_tokens:,}")
                logger.info(f"  - Completion tokens: {usage_data.completion_tokens:,}")
                logger.info(f"  - Total tokens: {usage_data.total_tokens:,}")

                # Calculate cost estimates (approximate, prices may vary)
                prompt_cost = usage_data.prompt_tokens * 0.00015 / 1000  # $0.15 per 1K tokens
                completion_cost = (
                    usage_data.completion_tokens * 0.0006 / 1000
                )  # $0.60 per 1K tokens
                total_cost = prompt_cost + completion_cost
                logger.info(f"  - Estimated cost: ${total_cost:.4f}")
            elif config.openai_model == "gpt-5":
                logger.info(
                    "GPT-5 Responses API - token usage data not available in this API version"
                )
            else:
                logger.warning("Token usage data not available from OpenAI response")

        except Exception as e:
            logger.error(f"OpenAI API error during transcript processing: {e}")
            raise APIError(f"OpenAI transcript processing failed: {e}", "openai")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_comments_summary(
        self, comments: CommentsData, config: PipelineConfig
    ) -> Iterator[str]:
        """Generate streaming summary of video comments"""

        logger.info(f"Generating comments summary for {comments.total_count} comments")
        logger.info("Comments input metrics:")
        logger.info(f"  - Total comments: {comments.total_count:,}")
        logger.info(f"  - Total word count: {comments.total_word_count:,}")
        logger.info(f"  - Estimated tokens: {comments.total_word_count * 4 // 3:,}")

        # Prepare comments data
        df = pd.DataFrame([comment.model_dump() for comment in comments.comments])
        df["date"] = pd.to_datetime(df["date"])
        df["num_replies"] = df["replies"].apply(len)

        # Sort by date and replies for better selection
        df = df.sort_values(by=["date", "num_replies"], ascending=[False, True])

        # Select comments up to limits
        selected_comments = []
        total_length = 0

        for _, row in df.iterrows():
            comment_length = len(row["comment"].split())
            if (
                len(selected_comments) < config.max_comments
                and total_length + comment_length <= config.max_total_word_length
            ):
                selected_comments.append(row)
                total_length += comment_length

        logger.info("Selected comments metrics:")
        logger.info(f"  - Selected comments: {len(selected_comments):,}")
        logger.info(f"  - Selected word count: {total_length:,}")
        logger.info(
            f"  - Selection ratio: {len(selected_comments) / comments.total_count * 100:.1f}%"
        )
        logger.info(f"  - Word ratio: {total_length / comments.total_word_count * 100:.1f}%")

        selected_df = pd.DataFrame(selected_comments)

        prompt = (
            f"Given the following user comments in their native language, "
            f"Understand the problem and core insights around the subject. "
            f"Summarise information so that includes core insights and guidelines and opportunities that can be useful in context to the problem. "
            f"Structure output as prioritised bullet points. Ranking should be done on basis of topic hotness and like count. "
            f"Capture and mention facts like prices, tools technologies, locations, people, organizations, financial data and links to products or other articles. etc. Include those in the summary for support. "
            f"Comments, Replies and Like Count:\n\n{selected_df[['comment', 'replies', 'like_count']].to_string(index=False)}\n\n"
        )

        # Split prompt if too long
        max_chunk_length = 1048576  # ~1MB limit
        prompt_chars = len(prompt)
        estimated_prompt_tokens = prompt_chars // 4

        logger.info("Comments prompt metrics:")
        logger.info(f"  - Prompt characters: {prompt_chars:,}")
        logger.info(f"  - Estimated prompt tokens: {estimated_prompt_tokens:,}")

        if len(prompt) > max_chunk_length:
            logger.warning(f"Prompt too long ({len(prompt)} chars), truncating")
            prompt = prompt[:max_chunk_length]

        try:
            import time

            start_time = time.time()

            logger.info("OpenAI API call starting (comments):")
            logger.info(f"  - Model: {config.openai_model}")
            logger.info("  - Temperature: 0.2")
            if config.openai_model == "gpt-5":
                logger.info("  - Reasoning Effort: low (for focused comments analysis)")
            else:
                logger.info("  - Stream: True")

            # For GPT-5, combine system prompt and user prompt
            if config.openai_model == "gpt-5":
                full_comments_prompt = f"{self.system_prompt}\n\n{prompt}"

                response = self.client.responses.create(
                    model=config.openai_model,
                    input=full_comments_prompt,
                    reasoning={"effort": "low"},  # Low effort for comments processing
                    # Note: GPT-5 Responses API doesn't support temperature parameter
                )

                # GPT-5 responses API doesn't support streaming
                output_content = response.output_text
                yield output_content
                usage_data = None

            else:
                # Fallback to chat completions for other models
                stream = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,  # Lower temperature for more focused analysis
                    model=config.openai_model,
                    stream=True,
                    stream_options={"include_usage": True},  # Get token usage with streaming
                )

                output_content = ""
                usage_data = None

                for chunk in stream:
                    if (
                        chunk.choices
                        and len(chunk.choices) > 0
                        and chunk.choices[0].delta.content is not None
                    ):
                        content = chunk.choices[0].delta.content
                        output_content += content
                        yield content

                    # Capture usage data from the final chunk
                    if hasattr(chunk, "usage") and chunk.usage is not None:
                        usage_data = chunk.usage

            # Calculate latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Log output metrics
            output_chars = len(output_content)
            output_words = len(output_content.split())
            estimated_output_tokens = output_chars // 4

            if config.openai_model == "gpt-5":
                logger.info("GPT-5 Responses API call completed (comments):")
            else:
                logger.info("OpenAI API call completed (comments):")
            logger.info(f"  - Latency: {latency_ms:.0f}ms")
            logger.info(f"  - Output characters: {output_chars:,}")
            logger.info(f"  - Output words: {output_words:,}")
            logger.info(f"  - Estimated output tokens: {estimated_output_tokens:,}")

            # Log actual token usage if available (for non-GPT-5 models)
            if config.openai_model != "gpt-5" and usage_data:
                logger.info("OpenAI token usage (actual, comments):")
                logger.info(f"  - Prompt tokens: {usage_data.prompt_tokens:,}")
                logger.info(f"  - Completion tokens: {usage_data.completion_tokens:,}")
                logger.info(f"  - Total tokens: {usage_data.total_tokens:,}")

                # Calculate cost estimates
                prompt_cost = usage_data.prompt_tokens * 0.00015 / 1000  # $0.15 per 1K tokens
                completion_cost = (
                    usage_data.completion_tokens * 0.0006 / 1000
                )  # $0.60 per 1K tokens
                total_cost = prompt_cost + completion_cost
                logger.info(f"  - Estimated cost: ${total_cost:.4f}")
            elif config.openai_model == "gpt-5":
                logger.info(
                    "GPT-5 Responses API - token usage data not available in this API version"
                )
            else:
                logger.warning("Token usage data not available from OpenAI response (comments)")

        except Exception as e:
            logger.error(f"OpenAI API error during comments processing: {e}")
            raise APIError(f"OpenAI comments processing failed: {e}", "openai")


class PromptTemplates:
    """Collection of prompt templates for different analysis tasks"""

    SUMMARIZE_FOR_REFLECTION = """
    Create an executive summary of this video transcript that delivers the actual content in a clear, informative narrative format.

    **Format Requirements:**
    
    1. Start with a TL;DR (2-3 sentences capturing the absolute essence)
    
    2. Main body structured as readable prose with:
       - Clear section headings for major topics/concepts
       - Information-dense paragraphs that tell the story
       - Smooth narrative flow that a busy executive could quickly scan
    
    **Content Principles:**
    
    - DELIVER the information, don't analyze the structure
    - Write as if briefing someone who needs to know what was said
    - Consolidate repetitive points into single, powerful statements
    - Preserve all critical facts:
       * Numbers, statistics, financial data, metrics
       * Dates, deadlines, timeframes
       * Names of people, companies, organizations, products
       * Technologies, tools, platforms, methodologies
       * Links, references, resources mentioned
       * Key quotes or memorable statements
    
    - Focus on:
       * Main arguments and conclusions
       * Actionable insights and recommendations
       * Novel information or surprising revelations
       * Practical applications and implications
    
    Write in a professional yet engaging tone. Make every sentence count. Remove filler while preserving substance. The reader should feel fully informed without watching the video.
    """

    QNA_TEMPLATE = """
    Please answer question below given the text provided. Focus to provide succint insights based on discussion. 
    For each insight capture relevant quote from the original text.
    
    Question: {question}
    """

    COMPRESS_CONTENT = """
    Analyze the text given below against given guidelines, finally take those remarks into account and generate new text, use single or multiple paragraphs. 
    Output just the refactored text. 
    Use following guidelines for content review:
    1. **Identify and Reduce Redundancy**:
       - In written communication, redundancy occurs when information is repetitive or unnecessary. By identifying and removing such redundant parts, you can make your text more concise and information-dense.
       - Use tools or techniques that analyze text for common phrases, cliches, or repeated ideas, and then refine your content to eliminate or rephrase these parts.
    2. **Focus on Novelty and Relevance** 
       - Aim to include novel, relevant, and interesting information in your communication.
       - This might mean presenting unique insights, lesser-known facts, or new perspectives on a topic. 
    3. Capture and mention facts
       - Facts are important to the reader, and should be captured and mentioned.
       - Numbers, dates, times, locations, people, organizations, financial data and etc. should be captured and mentioned.
       - links to products or other articles
       - Product and platform names, technologies, tools, and methodologies should be captured and mentioned.
    """

    @classmethod
    def get_qna_prompt(cls, question: str) -> str:
        """Get a QnA prompt with the specified question"""
        return cls.QNA_TEMPLATE.format(question=question)
