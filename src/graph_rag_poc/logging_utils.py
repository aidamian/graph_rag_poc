import json
import logging
from typing import Any

from rich.logging import RichHandler
from rich.markup import escape


CHANNEL_COLORS = {
    "API": "yellow",
    "GRAPH": "magenta",
    "RETRIEVE": "cyan",
    "LLM": "green",
    "INGEST": "bright_blue",
    "UI": "bright_white",
    "APP": "white",
}

_LOGGING_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_level=False,
        show_path=False,
        show_time=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    root.addHandler(handler)
    _LOGGING_CONFIGURED = True


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return escape(value)
    try:
        return escape(json.dumps(value, sort_keys=True))
    except TypeError:
        return escape(str(value))


class ChannelLogger:
    def __init__(self, channel: str):
        self.channel = channel
        self.logger = logging.getLogger(channel)

    def _emit(self, level: int, event: str, **fields: Any) -> None:
        color = CHANNEL_COLORS.get(self.channel, "white")
        prefix = f"[bold {color}]{escape(self.channel):<8}[/]"
        body = escape(event)
        if fields:
            serialized = " ".join(
                f"{escape(key)}={_format_value(value)}"
                for key, value in fields.items()
                if value is not None
            )
            body = f"{body} {serialized}"
        self.logger.log(level, f"{prefix} {body}")

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, event, **fields)

    def exception(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, event, **fields)
        self.logger.exception("")


def get_logger(channel: str) -> ChannelLogger:
    return ChannelLogger(channel)

