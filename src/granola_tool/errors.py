"""Typed exceptions for granola-tool."""


class GranolaError(Exception):
    """Base exception for all granola-tool errors."""


class CacheError(GranolaError):
    """Cache file not found or unreadable."""


class NotFoundError(GranolaError):
    """Meeting/document not found in cache."""


class ApiError(GranolaError):
    """API request failed."""


class TokenExpiredError(ApiError):
    """WorkOS access token has expired."""
