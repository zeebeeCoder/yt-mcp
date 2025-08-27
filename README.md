# YouTube Analysis Pipeline

**Stop watching long videos. Start getting smarter insights.**

Transform any YouTube video into structured analysis with AI-powered critical thinking and ready-to-research questions.

## What This Tool Does

### The Problem
- 📺 **Long videos eat your time** - 2-hour podcasts, lectures, and discussions
- 💬 **Comments contain valuable insights** - but they're scattered and hard to parse
- 🔍 **You want to research further** - but don't know what questions to ask
- 📝 **Taking notes is tedious** - and you miss important details

### The Solution
Give this tool any YouTube URL and get:

1. **📄 Executive Summary** - Key points from the entire video in minutes, not hours
2. **💡 Critical Analysis** - AI evaluates the content for clarity, accuracy, logic, and fairness  
3. **❓ Research Questions** - Prioritized follow-up questions you can hand off to Perplexity, ChatGPT, or Claude
4. **📊 Structured Output** - Clean Markdown reports perfect for documentation and sharing

### Example Output Structure
```
📽️ Video Information
├── Why everyone is worried about stocks right now!
├── Channel: Richard J Murphy
├── 150.7s processing time
└── 22,712 words transcript + 806 comments analyzed

🔍 Key Insights  
├── Market Crash Risks: Policy, AI, Deglobalization
├── • Overvaluation: Record S&P 500/FTSE despite weak fundamentals
├── • Drivers: Tariff inflation, consumer weakness, geopolitical risks
└── • Mitigation: Diversify, maintain liquidity, monitor policy response

🤔 Priority Questions for Research  
├── 1. How can we verify US market overvaluation claims independently?
├── 2. Can you quantify 'weakening fundamentals' with specific metrics?
├── 3. How do Austrian economics view current crash potential?
├── 4. What policy responses beyond Keynesian stimulus exist?
├── 5. Does historical crash pattern imply causation with current indicators?
└── 6. What alternative explanations exist for high valuations?

📋 Critical Thinking Assessment
├── Clarity: 8/10 - Clear central claim with structured arguments
├── Accuracy: 6/10 - Relies on indicators, needs more evidence  
├── Significance: 9/10 - Major economic implications globally
└── Fairness: 6/10 - Could benefit from more balanced perspectives
```

### Real-World Use Cases
- **📚 Academic Research** - Analyze lectures and extract research questions
- **💼 Business Intelligence** - Process industry discussions and identify opportunities  
- **🎓 Learning** - Get structured summaries from educational content
- **📰 News Analysis** - Extract key points and identify follow-up investigations

## Quick Start

### 1. Install
```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install yt-mcp globally
uv tool install git+https://github.com/zeebeeCoder/yt-mcp.git
```

### 2. Setup API Keys
You need API keys from:
- [YouTube Data API v3](https://developers.google.com/youtube/v3/getting-started)
- [OpenAI](https://platform.openai.com/api-keys) 
- [Google AI Studio](https://aistudio.google.com/app/apikey)

```bash
yt-setup  # Interactive setup - guides you through everything
```

### 3. Analyze Any Video
```bash
yt-analyze "https://www.youtube.com/watch?v=kg8RU3GDpsw"
```

That's it! Works from any directory.

## Usage Examples

### Basic Analysis
```bash
# Analyze any YouTube video
yt-analyze "https://www.youtube.com/watch?v=kg8RU3GDpsw"
```

### Save to File
```bash
# Generate Markdown report
yt-analyze "VIDEO_URL" --output analysis.md --format markdown

# Generate JSON for automation
yt-analyze "VIDEO_URL" --output data.json --format json
```

### Custom Analysis
```bash
# Focus on specific aspects
yt-analyze "VIDEO_URL" --instruction "What are the business insights and market opportunities?"

# Transcript only (faster)
yt-analyze "VIDEO_URL" --transcript-only
```

### Handoff to Research Tools
After running analysis, take the **Priority Questions** from the output and paste them into:
- **Perplexity** - for web research and fact-checking
- **ChatGPT/Claude** - for deeper analysis and discussion
- **Your notes** - for follow-up research topics

## Common Options
- `--instruction "custom focus"` - Direct the AI analysis
- `--output filename.md` - Save results to file  
- `--format markdown|json` - Choose output format
- `--transcript-only` - Skip comments (faster)
- `--verbose` - See detailed processing

## How It Works

**AI-Powered Analysis Chain:**
1. **Extract** - Downloads video transcript and top comments
2. **Summarize** - GPT-5 creates executive summary with key insights
3. **Compress** - Distills content into headline + bullet points
4. **Evaluate** - Assesses content against 8 critical thinking standards  
5. **Prioritize** - Generates 6 most impactful follow-up research questions

**Perfect for Research Handoffs:**
The priority questions are designed to be copy-pasted into research tools like Perplexity for deeper investigation.

## Troubleshooting

**API Keys Issues:**
```bash
yt-setup --show    # Check current status
yt-setup --validate # Test API connections
```

**Can't find yt-analyze command:**
- Make sure UV is in your PATH: `source ~/.bashrc` or restart terminal
- Reinstall: `uv tool install --force git+https://github.com/zeebeeCoder/yt-mcp.git`

**Slow processing:**
- Use `--transcript-only` to skip comments processing
- Large videos (2+ hours) can take 2-5 minutes

## License

MIT
