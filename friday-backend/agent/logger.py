"""
Centralized logging configuration for Project Friday.

Provides structured logging with:
- File rotation to prevent disk space issues
- Separate log levels for console and file
- Contextual information (module, function, line number)
- Performance tracking for critical operations
- Error tracing with full stack traces
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Log directory setup
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file paths
MAIN_LOG_FILE = LOG_DIR / "friday.log"
ERROR_LOG_FILE = LOG_DIR / "friday_errors.log"

# Custom log format with context
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Add custom fields if needed
        if not hasattr(record, "thread_id"):
            record.thread_id = ""
        return True


def setup_logger(
    name: str,
    level: int = logging.INFO,
    console_level: int = logging.WARNING,
) -> logging.Logger:
    """
    Create a configured logger instance.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: File logging level (default: INFO)
        console_level: Console logging level (default: WARNING)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Add context filter
    context_filter = ContextFilter()
    logger.addFilter(context_filter)

    # Console handler - only warnings and errors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        "%(levelname)s | %(name)s | %(message)s",
        datefmt=DATE_FORMAT,
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Main file handler - info and above (10MB max, 5 backups)
    file_handler = RotatingFileHandler(
        MAIN_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Error file handler - errors only (5MB max, 3 backups)
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    return logger


def log_function_call(logger: logging.Logger, func_name: str, **kwargs: Any) -> None:
    """
    Log a function call with its parameters.

    Args:
        logger: Logger instance
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    params = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    logger.debug(f"Calling {func_name}({params})")


def log_performance(logger: logging.Logger, operation: str, duration_ms: float) -> None:
    """
    Log performance metrics for an operation.

    Args:
        logger: Logger instance
        operation: Name of the operation
        duration_ms: Duration in milliseconds
    """
    if duration_ms > 1000:
        logger.warning(f"Slow operation: {operation} took {duration_ms:.2f}ms")
    else:
        logger.info(f"Performance: {operation} completed in {duration_ms:.2f}ms")


def log_graph_event(
    logger: logging.Logger,
    event_type: str,
    node_name: str,
    thread_id: str,
    details: str = "",
) -> None:
    """
    Log LangGraph execution events.

    Args:
        logger: Logger instance
        event_type: Type of event (start, end, error)
        node_name: Name of the graph node
        thread_id: Conversation thread ID
        details: Additional details
    """
    msg = f"Graph[{thread_id}] {event_type.upper()} node={node_name}"
    if details:
        msg += f" | {details}"
    logger.info(msg)


def log_tool_execution(
    logger: logging.Logger,
    tool_name: str,
    args: dict[str, Any],
    success: bool,
    result: str = "",
    error: str = "",
) -> None:
    """
    Log tool execution with results.

    Args:
        logger: Logger instance
        tool_name: Name of the tool
        args: Tool arguments
        success: Whether execution succeeded
        result: Result summary (if successful)
        error: Error message (if failed)
    """
    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    if success:
        logger.info(f"Tool[{tool_name}] SUCCESS | args=({args_str}) | result={result}")
    else:
        logger.error(f"Tool[{tool_name}] FAILED | args=({args_str}) | error={error}")


def log_checkpoint_operation(
    logger: logging.Logger,
    operation: str,
    thread_id: str,
    checkpoint_id: str = "",
    success: bool = True,
) -> None:
    """
    Log checkpoint save/load operations.

    Args:
        logger: Logger instance
        operation: Operation type (save, load, list)
        thread_id: Thread ID
        checkpoint_id: Checkpoint ID (if applicable)
        success: Whether operation succeeded
    """
    status = "SUCCESS" if success else "FAILED"
    msg = f"Checkpoint[{thread_id}] {operation.upper()} {status}"
    if checkpoint_id:
        msg += f" | checkpoint_id={checkpoint_id}"
    logger.info(msg)


def log_llm_call(
    logger: logging.Logger,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    duration_ms: float = 0,
) -> None:
    """
    Log LLM API calls with token usage.

    Args:
        logger: Logger instance
        provider: LLM provider name
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        duration_ms: Call duration in milliseconds
    """
    total_tokens = prompt_tokens + completion_tokens
    logger.info(
        f"LLM[{provider}/{model}] tokens={total_tokens} "
        f"(prompt={prompt_tokens}, completion={completion_tokens}) "
        f"duration={duration_ms:.2f}ms"
    )


# Create default logger for the agent module
default_logger = setup_logger("friday.agent")
