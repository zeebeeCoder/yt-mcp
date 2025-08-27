#!/usr/bin/env python3
"""
YouTube Analysis Pipeline - Main CLI Interface

A chain-of-thought data pipeline for analyzing YouTube videos through:
1. Extract - YouTube data (metadata, transcript, comments)
2. Process - AI summaries using OpenAI
3. Synthesize - Content compression with Google GenAI
4. Evaluate - Critical thinking standards assessment
5. Prioritize - Select most impactful follow-up questions
"""

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import Config, config, get_pipeline_config
from pipeline.chain import ChainProcessor
from pipeline.processors import PromptTemplates
from utils.credentials import interactive_setup, show_credential_status
from utils.errors import APIError, ConfigurationError, PipelineError
from utils.logging import get_logger, setup_logging

console = Console()
logger = get_logger(__name__)


def display_banner():
    """Display application banner"""
    banner = """
╭─────────────────────────────────────────╮
│      YouTube Analysis Pipeline          │
│    Chain-of-Thought Content Analysis    │
╰─────────────────────────────────────────╯
"""
    console.print(banner, style="bold blue")


def check_api_keys(env_file: str = None, config_dir: str = None):
    """Check and display API key status"""
    # Load configuration first
    Config.load_config(env_file, config_dir)

    validation = Config.validate_api_keys()
    missing = Config.get_missing_keys()

    if missing:
        table = Table(title="API Key Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")

        for service, valid in validation.items():
            status = "✓ Valid" if valid else "✗ Missing"
            style = "green" if valid else "red"
            table.add_row(service.replace("_", " ").title(), status, style=style)

        console.print(table)

        if missing:
            console.print(f"\n[red]Missing API keys: {', '.join(missing)}[/red]")
            console.print(
                "\n[yellow]Run 'yt-setup' to configure your API keys interactively.[/yellow]"
            )
            return False

    return True


def display_results(result, output_format: str = "rich", output_file: Optional[str] = None):
    """Display analysis results in specified format"""
    from pathlib import Path

    if output_format == "json":
        output_data = result.model_dump(mode="json")

        if output_file:
            output_path = Path(output_file).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2, default=str)
            console.print(f"[green]Results saved to: {output_path}[/green]")
        else:
            print(json.dumps(output_data, indent=2, default=str))

    elif output_format == "markdown":
        markdown_content = generate_markdown_report(result)

        if output_file:
            output_path = Path(output_file).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            console.print(f"[green]Markdown report saved to: {output_path}[/green]")
        else:
            print(markdown_content)

    elif output_format == "rich":
        # Display rich formatted results
        display_rich_results(result)

        if output_file:
            # Also save JSON version
            output_path = Path(output_file).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(result.model_dump(mode="json"), f, indent=2, default=str)
            console.print(f"\n[green]Results also saved to: {output_path}[/green]")


def generate_markdown_report(result) -> str:
    """Generate a clean Markdown report from analysis results"""
    from datetime import datetime

    # Header with video information
    report = f"""# YouTube Video Analysis Report

## 📽️ Video Information

**Title:** {result.video_metadata.title}  
**Channel:** {result.video_metadata.author}  
**Published:** {result.video_metadata.published_date.strftime("%B %d, %Y")}  
**URL:** {result.video_metadata.url}  
**Analysis Date:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}  
**Processing Time:** {result.total_processing_time:.1f} seconds  

---

## 📊 Data Extraction Summary

"""

    # Data extraction details
    if result.transcript and result.transcript.available:
        report += f"**Transcript:** ✅ Successfully extracted ({result.transcript.word_count:,} words)  \n"
    else:
        report += "**Transcript:** ❌ Not available or not processed  \n"

    if result.comments and result.comments.total_count > 0:
        report += f"**Comments:** ✅ Processed {result.comments.total_count:,} comments ({result.comments.total_word_count:,} words)  \n"
    else:
        report += "**Comments:** ❌ Not processed  \n"

    report += "\n---\n\n"

    # Individual Processing Summaries
    if result.transcript_summary:
        report += f"""## 📝 Transcript Summary

{result.transcript_summary}

---

"""

    if result.comments_summary:
        report += f"""## 💬 Comments Summary

{result.comments_summary}

---

"""

    # Main insights (compressed/synthesized)
    if result.compressed_summary:
        report += f"""## 🔍 Key Insights

{result.compressed_summary}

---

"""

    # Critical thinking questions
    if result.critical_assessment and result.critical_assessment.selected_questions:
        report += "## 🤔 Priority Questions for Further Investigation\n\n"
        for i, question in enumerate(result.critical_assessment.selected_questions, 1):
            report += f"{i}. {question}\n\n"
        report += "---\n\n"

    # Critical thinking standards (if available)
    if result.critical_assessment and result.critical_assessment.standards:
        report += "## 📋 Critical Thinking Assessment\n\n"
        for standard in result.critical_assessment.standards:
            report += f"### {standard.name} (Rating: {standard.rating}/10)\n\n"
            report += f"{standard.evaluation}\n\n"
            if standard.followup_questions:
                report += "**Follow-up Questions:**\n"
                for question in standard.followup_questions:
                    report += f"- {question}\n"
                report += "\n"
        report += "---\n\n"

    # Processing details
    report += "## ⚙️ Processing Steps\n\n"
    report += "| Step | Status | Time | Notes |\n"
    report += "|------|---------|---------|-------|\n"

    for step in result.processing_steps:
        status_emoji = "✅" if step.success else "❌"
        status_text = "Success" if step.success else "Failed"
        time_text = f"{step.processing_time:.2f}s"
        notes = step.error_message if step.error_message else step.output_data
        # Clean notes for markdown table (escape pipes and truncate)
        notes = notes.replace("|", "\\|").replace("\n", " ")[:50]
        if len(notes) > 50:
            notes += "..."

        report += f"| {step.step_name} | {status_emoji} {status_text} | {time_text} | {notes} |\n"

    report += f"""
---

## 📈 Analysis Summary

- **Total Processing Time:** {result.total_processing_time:.1f} seconds
- **Steps Completed:** {sum(1 for step in result.processing_steps if step.success)}/{len(result.processing_steps)}
- **Data Sources:** {len([x for x in [result.transcript, result.comments] if x and (x.available if hasattr(x, "available") else x.total_count > 0)])} of 2

---

*Report generated by YouTube Analysis Pipeline - Chain-of-Thought Content Analysis*
"""

    return report


def display_rich_results(result):
    """Display results with rich formatting"""

    # Video info
    video_panel = Panel(
        f"[bold]{result.video_metadata.title}[/bold]\n"
        f"Channel: {result.video_metadata.author}\n"
        f"Published: {result.video_metadata.published_date.strftime('%Y-%m-%d')}\n"
        f"Processing time: {result.total_processing_time:.2f}s",
        title="Video Information",
        title_align="left",
    )
    console.print(video_panel)

    # Data extraction summary
    if result.transcript:
        transcript_info = f"Transcript: {'✓' if result.transcript.available else '✗'} ({result.transcript.word_count} words)"
    else:
        transcript_info = "Transcript: Not processed"

    if result.comments and result.comments.total_count > 0:
        comments_info = f"Comments: {result.comments.total_count} items ({result.comments.total_word_count} words)"
    else:
        comments_info = "Comments: Not processed"

    extraction_panel = Panel(
        f"{transcript_info}\n{comments_info}", title="Data Extraction", title_align="left"
    )
    console.print(extraction_panel)

    # Compressed Summary (main result)
    if result.compressed_summary:
        summary_panel = Panel(
            result.compressed_summary,
            title="[bold]Key Insights[/bold]",
            title_align="center",
            border_style="green",
        )
        console.print(summary_panel)

    # Critical Thinking Assessment
    if result.critical_assessment and result.critical_assessment.selected_questions:
        console.print("\n[bold cyan]Priority Questions for Further Investigation:[/bold cyan]")

        for i, question in enumerate(result.critical_assessment.selected_questions, 1):
            console.print(f"[yellow]{i}.[/yellow] {question}")

    # Processing steps summary
    if result.processing_steps:
        console.print("\n[bold]Processing Steps:[/bold]")

        table = Table()
        table.add_column("Step", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Time", style="yellow")

        for step in result.processing_steps:
            status = "✓ Success" if step.success else "✗ Failed"
            style = "green" if step.success else "red"
            table.add_row(
                step.step_name.replace("_", " ").title(),
                status,
                f"{step.processing_time:.2f}s",
                style=style,
            )

        console.print(table)


@click.command()
@click.argument("video_url")
@click.option("--instruction", "-i", help="Custom instruction for transcript analysis")
@click.option("--max-comments", "-c", type=int, help="Maximum number of comments to process")
@click.option("--max-words", "-w", type=int, help="Maximum total word count for comments")
@click.option("--output", "-o", help="Output file path (supports absolute and relative paths)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["rich", "json", "markdown"]),
    default="rich",
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", help="Log file path")
# Credential options
@click.option("--env-file", help="Path to custom .env file with API keys")
@click.option("--config-dir", help="Path to custom configuration directory")
# Pipeline step controls
@click.option("--no-transcript", is_flag=True, help="Skip transcript extraction")
@click.option("--no-comments", is_flag=True, help="Skip comments extraction")
@click.option("--no-transcript-processing", is_flag=True, help="Skip transcript AI processing")
@click.option("--no-comments-processing", is_flag=True, help="Skip comments AI processing")
@click.option("--no-synthesis", is_flag=True, help="Skip content synthesis step")
@click.option("--no-evaluation", is_flag=True, help="Skip critical thinking evaluation")
@click.option(
    "--transcript-only", is_flag=True, help="Extract and process only transcript (shortcut)"
)
@click.option("--comments-only", is_flag=True, help="Extract and process only comments (shortcut)")
def analyze(
    video_url: str,
    instruction: str,
    max_comments: int,
    max_words: int,
    output: str,
    output_format: str,
    verbose: bool,
    log_file: str,
    env_file: str,
    config_dir: str,
    no_transcript: bool,
    no_comments: bool,
    no_transcript_processing: bool,
    no_comments_processing: bool,
    no_synthesis: bool,
    no_evaluation: bool,
    transcript_only: bool,
    comments_only: bool,
):
    """Analyze a YouTube video using the chain-of-thought pipeline"""

    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level, log_file=log_file)

    display_banner()

    # Check API keys with custom credential sources
    if not check_api_keys(env_file, config_dir):
        console.print(
            "\n[yellow]💡 Quick setup: Run 'yt-setup' to configure API keys interactively[/yellow]"
        )
        console.print(
            "[yellow]   or set environment variables: YOUTUBE_API_KEY, OPENAI_API_KEY, GOOGLE_GENAI_API_KEY[/yellow]"
        )
        sys.exit(1)

    try:
        # Handle shortcut options
        if transcript_only:
            no_comments = True
            no_comments_processing = True
        elif comments_only:
            no_transcript = True
            no_transcript_processing = True

        # Create pipeline configuration
        pipeline_config = get_pipeline_config(
            max_comments=max_comments,
            max_total_word_length=max_words,
            enable_transcript=not no_transcript,
            enable_comments=not no_comments,
            enable_transcript_processing=not no_transcript_processing,
            enable_comments_processing=not no_comments_processing,
            enable_synthesis=not no_synthesis,
            enable_evaluation=not no_evaluation,
        )

        # Initialize processor with current API keys
        processor = ChainProcessor(
            youtube_api_key=config.YOUTUBE_API_KEY,
            openai_api_key=config.OPENAI_API_KEY,
            google_genai_api_key=config.GOOGLE_GENAI_API_KEY,
        )

        # Use custom instruction or default
        analysis_instruction = instruction or PromptTemplates.SUMMARIZE_FOR_REFLECTION

        console.print(f"\n[cyan]Analyzing video: {video_url}[/cyan]")

        with console.status("[bold green]Processing...", spinner="dots"):
            result = processor.analyze_video(
                video_url=video_url, config=pipeline_config, instruction=analysis_instruction
            )

        console.print("\n[green]✓ Analysis completed![/green]")
        display_results(result, output_format, output)

    except ConfigurationError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        sys.exit(1)
    except APIError as e:
        console.print(f"[red]API Error ({e.api_name}): {e}[/red]")
        sys.exit(1)
    except PipelineError as e:
        console.print(f"[red]Pipeline Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            raise
        sys.exit(1)


@click.group()
def cli():
    """YouTube Analysis Pipeline - Chain-of-Thought Content Analysis"""
    pass


@cli.command()
@click.option("--show", is_flag=True, help="Show current configuration status")
@click.option("--validate", is_flag=True, help="Validate API keys without setup")
@click.option("--env-file", help="Path to custom .env file")
@click.option("--config-dir", help="Path to custom configuration directory")
def setup(show: bool, validate: bool, env_file: str, config_dir: str):
    """Setup configuration and check API keys"""
    display_banner()

    if show:
        show_credential_status(env_file, config_dir)
        return

    if validate:
        Config.load_config(env_file, config_dir)
        validation = Config.validate_api_keys()
        missing = Config.get_missing_keys()

        if not missing:
            console.print("[green]✓ All API keys are valid![/green]")
        else:
            console.print(f"[red]✗ Invalid or missing keys: {', '.join(missing)}[/red]")
        return

    # Interactive setup
    success = interactive_setup()

    if success:
        # Show configuration info
        console.print("\n[bold]Pipeline Configuration:[/bold]")
        pipeline_config = get_pipeline_config()

        table = Table()
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Max Comments", str(pipeline_config.max_comments))
        table.add_row("Max Total Words", str(pipeline_config.max_total_word_length))
        table.add_row("OpenAI Model", pipeline_config.openai_model)
        table.add_row("Gemini Model", pipeline_config.gemini_model)
        table.add_row("Selected Questions", str(pipeline_config.num_selected_questions))

        console.print(table)
        console.print(
            "\n[green]✓ Setup complete! You can now run 'yt-analyze' with any video URL.[/green]"
        )
    else:
        console.print(
            "\n[red]Setup incomplete. Please run 'yt-setup' again or manually edit your .env file.[/red]"
        )


# Add the analyze command to the CLI group
cli.add_command(analyze)


# Entry point functions for pyproject.toml scripts
def setup_command():
    """Entry point for yt-setup command"""
    setup()


if __name__ == "__main__":
    cli()
