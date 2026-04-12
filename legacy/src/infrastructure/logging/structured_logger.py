"""Structured logger implementation."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class StructuredLogger:
    """Structured logger for the application."""
    
    def __init__(
        self,
        log_file: Optional[Path] = None,
        level: LogLevel = LogLevel.INFO,
        enable_console: bool = True
    ):
        self.log_file = log_file
        self.level = level
        self.enable_console = enable_console
        
        # Create log directory if needed
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method."""
        if level.value < self.level.value:
            return
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.name,
            "message": message,
            **kwargs
        }
        
        # Format for console output
        console_message = self._format_console_message(log_entry)
        
        # Output to console
        if self.enable_console:
            print(console_message, file=sys.stderr if level.value >= LogLevel.WARNING.value else sys.stdout)
        
        # Write to file
        if self.log_file:
            asyncio.create_task(self._write_to_file(log_entry))
    
    def _format_console_message(self, log_entry: Dict[str, Any]) -> str:
        """Format log entry for console output."""
        timestamp = log_entry["timestamp"]
        level = log_entry["level"]
        message = log_entry["message"]
        
        # Add color codes for different levels
        color_codes = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "CRITICAL": "\033[35m", # Magenta
        }
        
        reset_code = "\033[0m"
        color = color_codes.get(level, "")
        
        # Format: [timestamp] LEVEL: message
        formatted = f"[{timestamp}] {color}{level}{reset_code}: {message}"
        
        # Add additional fields if present
        additional_fields = {k: v for k, v in log_entry.items() 
                           if k not in ["timestamp", "level", "message"]}
        if additional_fields:
            formatted += f" | {json.dumps(additional_fields)}"
        
        return formatted
    
    async def _write_to_file(self, log_entry: Dict[str, Any]):
        """Write log entry to file asynchronously."""
        try:
            log_line = json.dumps(log_entry) + "\n"
            
            await asyncio.to_thread(
                self._append_to_file,
                self.log_file,
                log_line
            )
        except Exception as e:
            # Fallback to synchronous write if async fails
            print(f"Failed to write to log file: {e}", file=sys.stderr)
    
    def _append_to_file(self, file_path: Path, content: str):
        """Append content to file (synchronous)."""
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
    
    def log_generation_start(self, prompt_hash: str, settings: Dict[str, Any]):
        """Log story generation start."""
        self.info(
            "story_generation_started",
            prompt_hash=prompt_hash,
            settings=settings
        )
    
    def log_generation_complete(self, story_id: str, word_count: int, duration: float):
        """Log story generation completion."""
        self.info(
            "story_generation_completed",
            story_id=story_id,
            word_count=word_count,
            duration=duration,
            words_per_minute=word_count / (duration / 60) if duration > 0 else 0
        )
    
    def log_model_call(self, model_name: str, provider: str, duration: float, token_count: Optional[int] = None):
        """Log model API call."""
        self.debug(
            "model_call",
            model_name=model_name,
            provider=provider,
            duration=duration,
            token_count=token_count,
            tokens_per_second=token_count / duration if token_count and duration > 0 else None
        )
    
    def log_error(self, error: Exception, context: Optional[str] = None):
        """Log error with context."""
        self.error(
            "error_occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        ) 