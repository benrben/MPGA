"""Shared FTS5 query utilities."""

from __future__ import annotations

# FTS5 boolean operators that must be treated as literals, not operators.
_FTS5_OPERATORS = frozenset({"OR", "AND", "NOT", "NEAR"})


def _escape_fts5_term(term: str) -> str:
    """Escape a single search token for safe use in an FTS5 MATCH expression.

    Wraps the token in double-quotes (FTS5 phrase syntax) and escapes any
    internal double-quote characters by doubling them (``"`` → ``""``).
    This ensures the token is treated as a literal string by the FTS5 engine,
    not as an operator or special syntax.

    Examples::

        _escape_fts5_term('hello')    ->  '"hello"'
        _escape_fts5_term('"hello"')  ->  '""hello""' wrapped in outer quotes
        _escape_fts5_term('OR')       ->  '"OR"'
        _escape_fts5_term('hello*')   ->  '"hello"*'

    The trailing ``*`` prefix-match operator is preserved *outside* the quoted
    phrase so that FTS5 still performs prefix matching on the literal stem.
    """
    # Strip a trailing '*' — we will re-attach it outside the quoted phrase.
    has_prefix_star = term.endswith("*")
    stem = term[:-1] if has_prefix_star else term

    # Escape internal double-quotes by doubling them.
    escaped = stem.replace('"', '""')
    quoted = f'"{escaped}"'

    if has_prefix_star:
        return f"{quoted}*"
    return quoted


def prefix_match_query(query: str) -> str:
    """Expand user search terms into safe FTS5 prefix queries.

    Each token from *query* is:

    1. Wrapped in double-quotes so it is treated as a literal phrase by FTS5,
       preventing injection of operators like ``OR``, ``AND``, ``NOT``,
       ``NEAR``, or syntax characters like ``-``, ``(``, ``)``, ``^``.
    2. Any internal double-quote characters are doubled (``"`` → ``""``) per
       FTS5 escaping rules.
    3. A trailing ``*`` is re-applied *outside* the quoted phrase to preserve
       prefix-match behaviour for bare terms.

    Bare terms (no trailing ``*``) automatically receive a ``*`` suffix so
    that ``'auth'`` matches ``'authentication'``.

    Args:
        query: Raw user-supplied search string (may contain FTS5 special chars).

    Returns:
        A safe FTS5 MATCH expression string.
    """
    terms: list[str] = []
    for raw_term in query.split():
        term = raw_term.strip()
        if not term:
            continue

        # Determine whether this bare term should get a prefix-match star.
        # We add it for all plain tokens; _escape_fts5_term will attach it
        # outside the quoted phrase so FTS5 still does prefix matching.
        already_has_star = term.endswith("*")
        if not already_has_star:
            term = term + "*"

        terms.append(_escape_fts5_term(term))

    return " ".join(terms)
