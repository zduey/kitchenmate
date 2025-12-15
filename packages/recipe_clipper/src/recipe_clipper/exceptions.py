"""Custom exceptions for recipe clipper."""


class RecipeClipperError(Exception):
    """Base exception for all recipe clipper errors."""

    pass


class RecipeNotFoundError(RecipeClipperError):
    """Raised when no recipe can be extracted from the URL."""

    pass


class RecipeParsingError(RecipeClipperError):
    """Raised when recipe parsing fails."""

    pass


class NetworkError(RecipeClipperError):
    """Raised when HTTP request fails."""

    pass


class LLMError(RecipeClipperError):
    """Raised when LLM API call fails."""

    pass
