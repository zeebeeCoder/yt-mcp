import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup application logging configuration"""

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(name)


class StepLogger:
    """Logger for tracking processing steps with timing"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.step_start_time: Optional[datetime] = None
        self.current_step: Optional[str] = None

    def start_step(self, step_name: str) -> None:
        """Start timing a processing step"""
        if self.current_step:
            self.logger.warning(f"Step '{self.current_step}' was not properly ended")

        self.current_step = step_name
        self.step_start_time = datetime.now()
        self.logger.info(f"Starting step: {step_name}")

    def end_step(self, success: bool = True, error_message: Optional[str] = None) -> float:
        """End timing a processing step and return duration"""
        if not self.current_step or not self.step_start_time:
            self.logger.warning("No active step to end")
            return 0.0

        duration = (datetime.now() - self.step_start_time).total_seconds()

        if success:
            self.logger.info(f"Completed step '{self.current_step}' in {duration:.2f}s")
        else:
            error_part = f" - Error: {error_message}" if error_message else ""
            self.logger.error(
                f"Step '{self.current_step}' failed after {duration:.2f}s{error_part}"
            )

        self.current_step = None
        self.step_start_time = None

        return duration

    def log_progress(self, message: str) -> None:
        """Log progress within the current step"""
        step_info = f" [{self.current_step}]" if self.current_step else ""
        self.logger.info(f"{message}{step_info}")
