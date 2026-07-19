"""
exceptions.py
-------------
Custom exception types so callers can distinguish failure modes precisely
instead of catching generic ValueError/RuntimeError everywhere. This also
lets app.py map each exception type to the correct HTTP status code
explicitly, rather than guessing from string content.
"""


class StadiumGenieError(Exception):
    """Base class for all application-specific errors."""


class InvalidInputError(StadiumGenieError):
    """Raised when user-supplied input fails validation. Maps to HTTP 400."""


class RateLimitExceededError(StadiumGenieError):
    """Raised when a client exceeds the request rate limit. Maps to HTTP 429."""


class AIServiceError(StadiumGenieError):
    """Raised when the GenAI backend is unavailable or errors. Maps to HTTP 503."""


class NotFoundError(StadiumGenieError):
    """Raised when a requested resource (gate, section) doesn't exist. Maps to HTTP 404."""
