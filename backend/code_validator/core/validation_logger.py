"""
Central logging system for code validation.
Thread-safe, structured JSON logging with session tracking.
"""

import json
import time
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import uuid


class LogLevel(Enum):
    """Log levels for filtering and prioritization."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class EventType(Enum):
    """All possible event types in the validation flow."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    CLI_INPUT = "cli_input"
    ENVIRONMENT_SETUP = "environment_setup"
    PROJECT_PARSING = "project_parsing"
    AGENT_ORCHESTRATION_START = "agent_orchestration_start"
    AGENT_EXECUTION_START = "agent_execution_start"
    STATIC_ANALYSIS_COMPLETE = "static_analysis_complete"
    LLM_DECISION = "llm_decision"
    LLM_CONTEXT_SELECTION = "llm_context_selection"
    LLM_CALL = "llm_call"
    LLM_RESPONSE = "llm_response"
    RESULT_FUSION = "result_fusion"
    AGENT_EXECUTION_COMPLETE = "agent_execution_complete"
    CROSS_AGENT_ANALYSIS = "cross_agent_analysis"
    RESULT_AGGREGATION = "result_aggregation"
    REPORT_GENERATION = "report_generation"
    ERROR = "error"


@dataclass
class LogContext:
    """Thread-local context for logging."""

    session_id: str
    agent_name: Optional[str] = None
    agent_type: Optional[str] = None


class ValidationLogger:
    """
    Central logger for validation sessions.
    Thread-safe, writes structured JSON logs.

    This is a singleton class - only one instance exists per process.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logger (only once due to singleton pattern)."""
        if not hasattr(self, "initialized"):
            self.log_file = None
            self.log_file_path = None
            self.session_id = None
            self.session_start_time = None
            self.write_lock = threading.Lock()
            self.context_storage = threading.local()
            self.log_buffer = []
            self.buffer_size = 100  # Flush after N entries
            self.enabled = True
            self.initialized = True

    def start_session(self, log_dir: str = "logs") -> str:
        """
        Start a new logging session.

        Args:
            log_dir: Directory to store log files

        Returns:
            Session ID for this validation run
        """
        self.session_id = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        self.session_start_time = time.time()

        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create log file
        self.log_file_path = log_path / f"validation_{self.session_id}.jsonl"
        self.log_file = open(self.log_file_path, "w", encoding="utf-8")

        self.log_event(
            EventType.SESSION_START,
            LogLevel.INFO,
            "validation_session",
            "Validation session started",
            {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "log_file": str(self.log_file_path),
            },
        )

        return self.session_id

    def end_session(self, success: bool = True):
        """
        End the current logging session.

        Args:
            success: Whether the validation completed successfully
        """
        elapsed = (
            time.time() - self.session_start_time if self.session_start_time else 0
        )

        self.log_event(
            EventType.SESSION_END,
            LogLevel.INFO,
            "validation_session",
            "Validation session ended",
            {
                "session_id": self.session_id,
                "success": success,
                "total_duration_ms": int(elapsed * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        self._flush()

        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def set_context(
        self, agent_name: Optional[str] = None, agent_type: Optional[str] = None
    ):
        """
        Set thread-local context for logging.

        Args:
            agent_name: Name of the agent (e.g., "security")
            agent_type: Type of the agent (e.g., "SECURITY")
        """
        if not hasattr(self.context_storage, "context"):
            self.context_storage.context = LogContext(session_id=self.session_id)

        if agent_name:
            self.context_storage.context.agent_name = agent_name
        if agent_type:
            self.context_storage.context.agent_type = agent_type

    def clear_context(self):
        """Clear thread-local context."""
        if hasattr(self.context_storage, "context"):
            self.context_storage.context.agent_name = None
            self.context_storage.context.agent_type = None

    @contextmanager
    def agent_context(self, agent_name: str, agent_type: str):
        """
        Context manager for agent execution.

        Usage:
            with logger.agent_context("security", "SECURITY"):
                # All logs in this block will have agent context
                logger.log_event(...)
        """
        self.set_context(agent_name, agent_type)
        try:
            yield
        finally:
            self.clear_context()

    def log_event(
        self,
        event_type: EventType,
        level: LogLevel,
        component: str,
        message: str,
        data: Dict[str, Any],
        execution_time_ms: Optional[int] = None,
    ):
        """
        Log a structured event.

        Args:
            event_type: Type of event (from EventType enum)
            level: Log level (from LogLevel enum)
            component: Component generating the log (e.g., "main", "coordinator", "agent")
            message: Human-readable message
            data: Event-specific structured data
            execution_time_ms: Optional execution time in milliseconds
        """
        if not self.enabled or not self.log_file:
            return

        # Get context
        context = {}
        if hasattr(self.context_storage, "context"):
            ctx = self.context_storage.context
            context = {
                "session_id": ctx.session_id,
                "agent_name": ctx.agent_name,
                "agent_type": ctx.agent_type,
            }
            if execution_time_ms is not None:
                context["execution_time_ms"] = execution_time_ms

        # Build log entry
        entry = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "level": level.value,
            "component": component,
            "message": message,
            "data": data,
            "context": context,
        }

        # Add to buffer
        with self.write_lock:
            self.log_buffer.append(entry)

            # Flush if buffer is full
            if len(self.log_buffer) >= self.buffer_size:
                self._flush()

    def log_error(
        self,
        component: str,
        message: str,
        exception: Exception,
        agent_name: Optional[str] = None,
    ):
        """
        Convenience method for logging errors.

        Args:
            component: Component where error occurred
            message: Error description
            exception: The exception object
            agent_name: Optional agent name if error is agent-specific
        """
        error_data = {
            "component": component,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "error_traceback": traceback.format_exc(),
        }

        if agent_name:
            error_data["agent_name"] = agent_name

        self.log_event(EventType.ERROR, LogLevel.ERROR, component, message, error_data)

    def _flush(self):
        """Flush log buffer to file (internal method)."""
        if not self.log_file or not self.log_buffer:
            return

        with self.write_lock:
            for entry in self.log_buffer:
                self.log_file.write(json.dumps(entry) + "\n")
            self.log_file.flush()
            self.log_buffer.clear()

    def get_log_file_path(self) -> Optional[str]:
        """
        Get current log file path.

        Returns:
            Path to the current log file, or None if no session is active
        """
        return str(self.log_file_path) if self.log_file_path else None


# Global logger instance (singleton)
logger = ValidationLogger()
