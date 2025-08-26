#!/usr/bin/env python3
"""
Basic usage examples for the YouTube Analysis Pipeline

This script demonstrates how to use the pipeline programmatically
without the CLI interface.
"""

import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config, get_pipeline_config
from pipeline.chain import ChainProcessor
from pipeline.processors import PromptTemplates
from utils.logging import setup_logging


def basic_example():
    """Basic example of analyzing a YouTube video"""

    # Setup logging
    setup_logging(level="INFO")

    print("YouTube Analysis Pipeline - Basic Example")
    print("=" * 50)

    # Check API keys
    missing_keys = Config.get_missing_keys()
    if missing_keys:
        print(f"Missing API keys: {missing_keys}")
        print("Please set up your .env file with API keys")
        return

    # Example video URL
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll as example

    # Create custom configuration
    config = get_pipeline_config(
        max_comments=100,  # Smaller for example
        max_total_word_length=10000,
        enable_transcript=True
    )

    # Initialize processor
    processor = ChainProcessor(
        youtube_api_key=Config.YOUTUBE_API_KEY,
        openai_api_key=Config.OPENAI_API_KEY,
        google_genai_api_key=Config.GOOGLE_GENAI_API_KEY
    )

    try:
        print(f"Analyzing video: {video_url}")

        # Run analysis
        result = processor.analyze_video(
            video_url=video_url,
            config=config,
            instruction=PromptTemplates.SUMMARIZE_FOR_REFLECTION
        )

        # Display results
        print(f"\nVideo: {result.video_metadata.title}")
        print(f"Channel: {result.video_metadata.author}")
        print(f"Processing time: {result.total_processing_time:.2f}s")

        if result.compressed_summary:
            print("\nKey Insights:")
            print("-" * 40)
            print(result.compressed_summary)

        if result.critical_assessment and result.critical_assessment.selected_questions:
            print("\nPriority Questions:")
            print("-" * 40)
            for i, question in enumerate(result.critical_assessment.selected_questions, 1):
                print(f"{i}. {question}")

        print("\nProcessing Steps:")
        print("-" * 40)
        for step in result.processing_steps:
            status = "✓" if step.success else "✗"
            print(f"{status} {step.step_name}: {step.processing_time:.2f}s")

        print("\n✓ Analysis completed successfully!")

    except Exception as e:
        print(f"Error during analysis: {e}")
        raise


def custom_instruction_example():
    """Example with custom analysis instruction"""

    # Custom instruction for specific analysis
    custom_instruction = PromptTemplates.get_qna_prompt(
        "What are the main technical concepts discussed and how do they relate to current industry trends?"
    )

    config = get_pipeline_config(max_comments=50)

    processor = ChainProcessor(
        youtube_api_key=Config.YOUTUBE_API_KEY,
        openai_api_key=Config.OPENAI_API_KEY,
        google_genai_api_key=Config.GOOGLE_GENAI_API_KEY
    )

    # Example tech video
    video_url = "https://www.youtube.com/watch?v=example"

    try:
        result = processor.analyze_video(
            video_url=video_url,
            config=config,
            instruction=custom_instruction
        )

        print("Custom Analysis Results:")
        print(result.compressed_summary)

    except Exception as e:
        print(f"Analysis failed: {e}")


def batch_analysis_example():
    """Example of analyzing multiple videos"""

    video_urls = [
        "https://www.youtube.com/watch?v=example1",
        "https://www.youtube.com/watch?v=example2",
        "https://www.youtube.com/watch?v=example3"
    ]

    config = get_pipeline_config(
        max_comments=200,
        enable_transcript=True
    )

    processor = ChainProcessor(
        youtube_api_key=Config.YOUTUBE_API_KEY,
        openai_api_key=Config.OPENAI_API_KEY,
        google_genai_api_key=Config.GOOGLE_GENAI_API_KEY
    )

    results = []

    for i, video_url in enumerate(video_urls, 1):
        print(f"Processing video {i}/{len(video_urls)}: {video_url}")

        try:
            result = processor.analyze_video(
                video_url=video_url,
                config=config
            )

            results.append({
                "url": video_url,
                "title": result.video_metadata.title,
                "summary": result.compressed_summary,
                "questions": result.critical_assessment.selected_questions if result.critical_assessment else []
            })

            print(f"✓ Completed: {result.video_metadata.title}")

        except Exception as e:
            print(f"✗ Failed: {e}")
            results.append({
                "url": video_url,
                "error": str(e)
            })

    # Save batch results
    import json
    with open("batch_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n✓ Batch analysis completed. Results saved to batch_analysis_results.json")


if __name__ == "__main__":
    # Run basic example
    basic_example()

    print("\n" + "=" * 50)
    print("For more examples, uncomment the lines below:")
    print("# custom_instruction_example()")
    print("# batch_analysis_example()")
