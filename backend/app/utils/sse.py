"""Server-Sent Events helpers."""


def sse_event(event: str, data: str) -> str:
    """Format a Server-Sent Event."""
    escaped = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {escaped}\n\n"
