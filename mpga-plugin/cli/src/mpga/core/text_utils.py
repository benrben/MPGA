"""Text utility helpers for the MPGA CLI."""

__all__ = ["truncate_string"]

_ELLIPSIS = "..."
_ELLIPSIS_LEN = len(_ELLIPSIS)  # 3


def truncate_string(s: str, max_len: int) -> str:
    """Return *s* truncated to *max_len* characters, appending '...' if cut.

    The ellipsis itself occupies 3 characters, so *max_len* must be at least 3
    to leave room for at least one character of content after truncation.

    Args:
        s: The string to (potentially) truncate.
        max_len: Maximum allowed length of the returned string.

    Returns:
        The original string when ``len(s) <= max_len``, otherwise
        ``s[:max_len - 3] + "..."``.

    Raises:
        ValueError: When *max_len* is less than 3.
    """
    if max_len < _ELLIPSIS_LEN:
        raise ValueError(f"max_len must be >= {_ELLIPSIS_LEN}")
    if len(s) <= max_len:
        return s
    return s[: max_len - _ELLIPSIS_LEN] + _ELLIPSIS
