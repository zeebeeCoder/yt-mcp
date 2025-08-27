# YouTube Analysis Pipeline

A chain-of-thought data pipeline for deep analysis of YouTube video content through AI processing.

## Overview

This pipeline transforms YouTube videos into structured insights through a 5-step chain-of-thought process:

1. **Extract** - YouTube data (metadata, transcript, comments)
2. **Process** - AI summaries using OpenAI GPT-5 with enhanced reasoning
3. **Synthesize** - Content compression with Google GenAI
4. **Evaluate** - Critical thinking standards assessment
5. **Prioritize** - Select most impactful follow-up questions

## Features

- 🎥 **YouTube Integration** - Extracts video metadata, transcripts, and comments
- 🤖 **AI Processing** - Uses OpenAI GPT-5 with enhanced reasoning capabilities for content analysis
- 🔍 **Critical Thinking** - Evaluates content against 8 critical thinking standards
- 📊 **Smart Prioritization** - Generates priority questions for deeper investigation
- 🎯 **Chain-of-Thought** - Structured thinking process for comprehensive analysis
- 💻 **CLI Interface** - Easy-to-use command line tool with rich formatting
- 🔧 **Configurable** - Customizable processing parameters
- 📝 **Multiple Output Formats** - Rich console display, JSON export, or Markdown reports
- 🛠️ **Flexible Pipeline Control** - Enable/disable individual processing steps
- 🚀 **YT-DLP Integration** - Robust transcript extraction with fallback mechanisms

## Installation

### Prerequisites

- Python 3.9-3.13
- API keys for:
  - YouTube Data API v3
  - OpenAI API
  - Google GenAI (Gemini)

### Installation from Source

#### Method 1: Using UV Package Manager (Recommended)

UV handles dependency management and Python version compatibility automatically.

1. Install UV (if not already installed):
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows  
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Clone and install:
```bash
git clone <repository-url>
cd yt-mcp
uv sync
```

3. Run interactive setup:
```bash
uv run yt-setup
```

4. Use from anywhere:
```bash
uv run yt-analyze "VIDEO_URL"
```

#### Method 2: Using pip (Python 3.9-3.13)

**Note**: All Python versions 3.9-3.13 are now fully supported with updated dependencies.

1. Clone the repository:
```bash
git clone <repository-url>
cd yt-mcp
```

2. Install in development mode:
```bash
pip install -e .
```

3. Run interactive setup:
```bash
yt-setup
```

The setup will guide you through configuring your API keys and create a configuration file at `~/.config/yt-mcp/.env`.

#### Testing Your Installation

Run the test script to verify everything works:

```bash
# For UV installation
uv run python test_installation.py

# For pip installation  
python test_installation.py
```

This will test all CLI commands and confirm your installation is working correctly.

## Usage

### Command Line Interface

#### If you used UV installation:
```bash
# Basic usage (works from any directory)
uv run yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID"

# Advanced options  
uv run yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --instruction "What are the key technical insights?" \
  --max-comments 1000 \
  --max-words 50000 \
  --output ~/Documents/analysis.md \
  --format markdown \
  --verbose
```

#### If you used pip installation:
```bash
# Basic usage (works from any directory)
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID"

# Advanced options
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --instruction "What are the key technical insights?" \
  --max-comments 1000 \
  --max-words 50000 \
  --output ~/Documents/analysis.md \
  --format markdown \
  --verbose
```

### Credential Management

The tool automatically finds credentials in this order:
1. `--env-file /path/to/custom/.env` (if specified)
2. `.env` in current directory
3. `~/.config/yt-mcp/.env` (created by `yt-setup`)
4. System environment variables

#### Credential Commands

**UV Installation:**
```bash
# Interactive setup (recommended)
uv run yt-setup

# Show current credential status
uv run yt-setup --show

# Validate API keys
uv run yt-setup --validate

# Use custom credential file
uv run yt-analyze "URL" --env-file /path/to/.env
```

**Pip Installation:**
```bash
# Interactive setup (recommended)
yt-setup

# Show current credential status
yt-setup --show

# Validate API keys
yt-setup --validate

# Use custom credential file
yt-analyze "URL" --env-file /path/to/.env
```

### Command Options

#### Content & Processing
- `--instruction, -i` - Custom instruction for transcript analysis
- `--max-comments, -c` - Maximum number of comments to process (default: 5000)
- `--max-words, -w` - Maximum total word count for comments (default: 80000)
- `--transcript-only` - Extract and process only transcript (faster)
- `--comments-only` - Extract and process only comments

#### Output & Formatting  
- `--output, -o` - Output file path (supports absolute and relative paths)
- `--format` - Output format: `rich` (default), `json`, or `markdown`
- `--verbose, -v` - Enable verbose logging
- `--log-file` - Log file path

#### Credentials & Configuration
- `--env-file` - Path to custom .env file with API keys
- `--config-dir` - Path to custom configuration directory

#### Pipeline Control
- `--no-transcript` - Skip transcript extraction
- `--no-comments` - Skip comments extraction
- `--no-transcript-processing` - Skip transcript AI processing
- `--no-comments-processing` - Skip comments AI processing  
- `--no-synthesis` - Skip content synthesis step
- `--no-evaluation` - Skip critical thinking evaluation

### Programmatic Usage

```python
from config import Config, get_pipeline_config
from pipeline.chain import ChainProcessor

# Create processor
processor = ChainProcessor(
    youtube_api_key=Config.YOUTUBE_API_KEY,
    openai_api_key=Config.OPENAI_API_KEY,
    google_genai_api_key=Config.GOOGLE_GENAI_API_KEY
)

# Configure pipeline
config = get_pipeline_config(
    max_comments=1000,
    enable_transcript=True
)

# Analyze video
result = processor.analyze_video(
    video_url="https://www.youtube.com/watch?v=VIDEO_ID",
    config=config
)

print(result.compressed_summary)
for question in result.critical_assessment.selected_questions:
    print(f"- {question}")
```

## Architecture

### Project Structure

```
yt-mcp/
├── main.py                    # CLI entry point
├── config.py                  # Configuration management
├── requirements.txt           # Dependencies
├── pipeline/
│   ├── chain.py              # Main ChainProcessor orchestrator
│   ├── extractors.py         # YouTube data extraction
│   ├── processors.py         # OpenAI processing
│   ├── synthesizers.py       # Google GenAI synthesis
│   └── evaluators.py         # Critical thinking evaluation
├── models/
│   └── schemas.py            # Pydantic data models
├── utils/
│   ├── logging.py            # Logging utilities
│   └── errors.py             # Error handling
└── examples/
    └── basic_usage.py        # Usage examples
```

### Data Flow

```
Video URL → Extract Metadata → Extract Transcript & Comments
    ↓
Process with OpenAI → Transcript Summary + Comments Summary
    ↓
Synthesize with GenAI → Compressed Insights
    ↓
Evaluate with Critical Thinking → Standards Assessment
    ↓
Prioritize Questions → Final Analysis Result
```

### Critical Thinking Standards

The pipeline evaluates content against 8 critical thinking standards:

1. **Clarity** - Are statements clear and understandable?
2. **Accuracy** - Is the information truthful and correct?
3. **Precision** - Are details specific enough?
4. **Depth** - Does analysis address underlying complexities?
5. **Breadth** - Are multiple perspectives considered?
6. **Logic** - Do conclusions follow from evidence?
7. **Significance** - Are important issues prioritized?
8. **Fairness** - Is thinking unbiased and justified?

## Configuration

### Pipeline Configuration

```python
config = PipelineConfig(
    max_comments=5000,              # Max comments to process
    max_total_word_length=80000,    # Max total words in comments
    openai_model="gpt-5",           # GPT-5 with enhanced reasoning and Responses API
    openai_temperature=0.35,        # OpenAI temperature
    gemini_model="gemini-2.5-flash-preview-04-17",  # Gemini model
    gemini_temperature=0.5,         # Gemini temperature
    num_selected_questions=6,       # Number of priority questions
    enable_transcript=True,         # Process transcript
    enable_audio_download=False     # Download audio (future feature)
)
```

### Environment Variables

- `YOUTUBE_API_KEY` - YouTube Data API v3 key
- `OPENAI_API_KEY` - OpenAI API key
- `GOOGLE_GENAI_API_KEY` - Google GenAI API key

## Examples

### Basic Analysis
```bash
yt-analyze "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Custom Instruction
```bash
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --instruction "What are the main business insights and market opportunities discussed?"
```

### Export Results

JSON format:
```bash
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --output ~/Documents/analysis.json \
  --format json
```

Markdown report:
```bash
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --output ~/Reports/report.md \
  --format markdown
```

### Pipeline Step Control

Process only transcript (faster):
```bash
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --transcript-only
```

Skip specific steps:
```bash
yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" \
  --no-synthesis \
  --no-evaluation
```

### Working with Custom Credentials

Using a project-specific .env file:
```bash
cd /path/to/project
yt-analyze "VIDEO_URL" --env-file ./.env --output ./analysis.md
```

Using system environment variables:
```bash
export YOUTUBE_API_KEY="your_key"
export OPENAI_API_KEY="your_key"
export GOOGLE_GENAI_API_KEY="your_key"
yt-analyze "VIDEO_URL"
```

## Output Format

### Rich Console Output
- Video metadata and processing summary
- Key insights in highlighted panels
- Priority questions for further investigation
- Processing steps with timing information

### JSON Output
```json
{
  "video_metadata": {
    "title": "Video Title",
    "author": "Channel Name",
    "published_date": "2024-01-01T00:00:00Z"
  },
  "compressed_summary": "Key insights...",
  "critical_assessment": {
    "selected_questions": [
      "Question 1...",
      "Question 2..."
    ]
  },
  "total_processing_time": 45.2
}
```

### Markdown Report Output
Professional structured reports with:
- 📽️ Video information and metadata
- 📊 Data extraction summary 
- 🔍 Key insights and compressed analysis
- 🤔 Priority questions for investigation
- 📋 Critical thinking assessment with ratings
- ⚙️ Processing steps table with timing
- 📈 Analysis summary and metrics

## Error Handling

The pipeline includes comprehensive error handling:

- **API Errors** - Handles rate limits, authentication issues
- **Data Validation** - Validates all inputs and outputs
- **Retry Logic** - Automatic retries for transient failures
- **Graceful Degradation** - Continues processing when non-critical steps fail

## Logging

Structured logging with multiple levels:

```bash
# Basic logging
uv run python main.py analyze URL

# Verbose logging
uv run python main.py analyze URL --verbose

# Log to file
uv run python main.py analyze URL --log-file analysis.log
```

## Performance

### Typical Processing Times
- Transcript-only processing: 15-30 seconds
- Small video (< 100 comments): 30-60 seconds
- Medium video (500-1000 comments): 1-2 minutes  
- Large video (5000+ comments): 3-5 minutes

### Resource Usage
- Memory: ~100-500 MB during processing
- API calls: 3-6 requests total (YouTube + OpenAI + GenAI)
- Storage: JSON outputs typically < 100 KB

## Limitations

- **YouTube API**: Rate limits apply (10,000 requests/day default)
- **Transcript Availability**: Not all videos have transcripts (YT-DLP provides robust extraction with fallbacks)
- **Comment Languages**: Works best with English content
- **API Costs**: OpenAI and GenAI usage incurs costs
- **Processing Time**: Large videos may take several minutes

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone <repository-url>
cd yt-mcp
uv sync --dev  # Install with development dependencies

# Run linting and type checks
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# Run tests
uv run pytest
uv run pytest --cov  # With coverage
```

### Development Commands

```bash
# Format code
uv run ruff format .

# Fix linting issues
uv run ruff check . --fix

# Run specific test
uv run pytest tests/test_config.py -v

# Install new dependency
uv add package-name
uv add --dev package-name  # Development dependency
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Setup development environment with `uv sync --dev`
4. Make changes with tests and proper formatting
5. Run linting and tests: `uv run ruff check . && uv run pytest`
6. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
1. Check the logs with `--verbose` flag
2. Verify API keys are configured correctly
3. Ensure video URL is accessible and public
4. Check API rate limits and quotas

Common issues:
- **"Missing API keys"**: Configure `.env` file
- **"Video not found"**: Check URL and video privacy
- **"Rate limit exceeded"**: Wait and retry, or increase quotas
- **"Transcript unavailable"**: YT-DLP will try multiple extraction methods automatically
- **"XML parsing errors"**: Fixed with YT-DLP integration (robust subtitle format support)