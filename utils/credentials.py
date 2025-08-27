"""
Credential management utilities for YouTube Analysis Pipeline
Handles multi-location credential discovery and secure loading
"""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console

console = Console()


def get_user_config_dir() -> Path:
    """Get user configuration directory following OS conventions"""
    if sys.platform == "win32":
        # Windows: %APPDATA%\yt-mcp
        config_dir = Path(os.environ.get("APPDATA", "")) / "yt-mcp"
    else:
        # Linux/macOS: ~/.config/yt-mcp
        config_dir = Path.home() / ".config" / "yt-mcp"

    return config_dir


def find_env_file(
    env_file: Optional[str] = None, config_dir: Optional[str] = None
) -> Optional[Path]:
    """
    Find .env file using priority order:
    1. Explicit --env-file path
    2. Custom --config-dir path
    3. Current directory .env
    4. User config directory ~/.config/yt-mcp/.env
    """
    search_paths = []

    # Priority 1: Explicit env file path
    if env_file:
        env_path = Path(env_file)
        if env_path.exists():
            return env_path
        else:
            console.print(f"[red]Specified env file not found: {env_file}[/red]")
            return None

    # Priority 2: Custom config directory
    if config_dir:
        config_path = Path(config_dir) / ".env"
        if config_path.exists():
            return config_path
        search_paths.append(config_path)

    # Priority 3: Current directory
    current_env = Path(".env")
    if current_env.exists():
        return current_env
    search_paths.append(current_env)

    # Priority 4: User config directory
    user_config_env = get_user_config_dir() / ".env"
    if user_config_env.exists():
        return user_config_env
    search_paths.append(user_config_env)

    # No .env file found
    return None


def load_credentials(
    env_file: Optional[str] = None, config_dir: Optional[str] = None
) -> Optional[Path]:
    """
    Load credentials with priority-based discovery
    Returns the path of the loaded .env file or None if using system environment
    """
    env_path = find_env_file(env_file, config_dir)

    if env_path:
        load_dotenv(env_path, override=True)
        return env_path

    # Fall back to system environment variables
    # Check if any required keys exist in environment
    required_keys = ["YOUTUBE_API_KEY", "OPENAI_API_KEY", "GOOGLE_GENAI_API_KEY"]
    system_keys = [key for key in required_keys if os.getenv(key)]

    if system_keys:
        return None  # Using system environment

    # No credentials found anywhere
    return None


def validate_api_keys() -> dict[str, bool]:
    """Validate that required API keys are present and non-empty"""
    return {
        "youtube": bool(os.getenv("YOUTUBE_API_KEY", "").strip()),
        "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "google_genai": bool(os.getenv("GOOGLE_GENAI_API_KEY", "").strip()),
    }


def get_missing_keys() -> list[str]:
    """Get list of missing API keys"""
    validation = validate_api_keys()
    return [key for key, valid in validation.items() if not valid]


def create_user_config_env() -> Path:
    """Create user config directory and .env file"""
    config_dir = get_user_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    env_file = config_dir / ".env"

    if not env_file.exists():
        template_content = """# YouTube Data API v3 key
# Get from: https://console.developers.google.com/
YOUTUBE_API_KEY=

# OpenAI API key  
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Google GenAI (Gemini) API key
# Get from: https://makersuite.google.com/app/apikey
GOOGLE_GENAI_API_KEY=
"""
        env_file.write_text(template_content)

    return env_file


def interactive_setup() -> bool:
    """Interactive setup to collect API keys from user"""
    console.print("\n[bold cyan]YouTube Analysis Pipeline Setup[/bold cyan]")
    console.print("Please provide your API keys. You can get these from:")
    console.print("• YouTube Data API: https://console.developers.google.com/")
    console.print("• OpenAI API: https://platform.openai.com/api-keys")
    console.print("• Google GenAI: https://makersuite.google.com/app/apikey\n")

    # Create config directory and get env file path
    env_file = create_user_config_env()

    # Read current .env content
    env_content = env_file.read_text()

    # Interactive prompts for each key
    keys_to_collect = [
        ("YOUTUBE_API_KEY", "YouTube Data API key"),
        ("OPENAI_API_KEY", "OpenAI API key"),
        ("GOOGLE_GENAI_API_KEY", "Google GenAI API key"),
    ]

    updated = False
    for key_name, key_description in keys_to_collect:
        current_value = os.getenv(key_name, "")

        if current_value:
            console.print(f"[green]✓ {key_description}: Already configured[/green]")
            continue

        while True:
            value = console.input(f"Enter {key_description}: ").strip()
            if value:
                # Replace or add the key in .env content
                lines = env_content.split("\n")
                key_found = False

                for i, line in enumerate(lines):
                    if line.startswith(f"{key_name}="):
                        lines[i] = f"{key_name}={value}"
                        key_found = True
                        break

                if not key_found:
                    lines.append(f"{key_name}={value}")

                env_content = "\n".join(lines)
                updated = True
                break
            else:
                console.print("[yellow]API key cannot be empty. Please try again.[/yellow]")

    # Write updated content if any changes
    if updated:
        env_file.write_text(env_content)
        console.print(f"\n[green]✓ Configuration saved to: {env_file}[/green]")

        # Reload environment to validate
        load_dotenv(env_file, override=True)

    # Validate the configuration
    validation = validate_api_keys()
    missing = get_missing_keys()

    if not missing:
        console.print("[green]✓ All API keys are configured correctly![/green]")
        return True
    else:
        console.print(f"[red]✗ Missing API keys: {', '.join(missing)}[/red]")
        console.print(f"Please edit {env_file} and add the missing keys.")
        return False


def show_credential_status(
    env_file: Optional[str] = None, config_dir: Optional[str] = None
) -> None:
    """Show current credential configuration status"""
    console.print("\n[bold]Credential Configuration Status[/bold]")

    # Load and show source
    credential_source = load_credentials(env_file, config_dir)
    if credential_source:
        console.print(f"Source: [cyan]{credential_source}[/cyan]")
    else:
        console.print("Source: [cyan]System environment variables[/cyan]")

    # Show validation status
    validation = validate_api_keys()
    missing = get_missing_keys()

    from rich.table import Table

    table = Table(title="API Key Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")

    for service, valid in validation.items():
        status = "✓ Valid" if valid else "✗ Missing"
        style = "green" if valid else "red"
        table.add_row(service.replace("_", " ").title(), status, style=style)

    console.print(table)

    if missing:
        console.print("\n[yellow]Run 'yt-setup' to configure missing API keys.[/yellow]")
