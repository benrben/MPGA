"""Click group for `mpga index` commands — external content indexing."""
from __future__ import annotations

import hashlib
import re
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import click

from mpga.core.config import find_project_root
from mpga.db.connection import open_db


class _TitleExtractor(HTMLParser):
    """Minimal HTML parser that extracts the <title> text."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(html: str) -> str:
    return _TAG_RE.sub("", html).strip()


def _extract_title(html: str) -> str:
    parser = _TitleExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.title.strip() or "Untitled"


@click.group("index", help="Index external content — URLs, docs, and more")
def index_cmd() -> None:
    pass


@index_cmd.command("url", help="Fetch and index a URL")
@click.argument("url")
def index_url(url: str) -> None:
    try:
        with urlopen(url) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "text/html")
    except (URLError, OSError) as exc:
        click.echo(f"Error: Failed to fetch {url} — {exc}")
        return

    html = raw.decode("utf-8", errors="replace")
    title = _extract_title(html)
    text_content = _strip_tags(html)
    content_hash = hashlib.sha256(raw).hexdigest()

    root = find_project_root()
    with closing(open_db(root)) as conn:
        existing = conn.execute(
            "SELECT id, content_hash FROM indexed_content WHERE url = ?", (url,)
        ).fetchone()

        if existing:
            if existing[1] == content_hash:
                click.echo(f"Already indexed (unchanged): {url}")
                return
            conn.execute(
                "UPDATE indexed_content SET title=?, content=?, content_type=?, "
                "content_hash=?, fetched_at=datetime('now') WHERE id=?",
                (title, text_content, content_type, content_hash, existing[0]),
            )
            conn.commit()
            click.echo(f"Updated indexed content: {title} ({url})")
            return

        conn.execute(
            "INSERT INTO indexed_content (url, title, content, content_type, content_hash, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (url, title, text_content, content_type, content_hash),
        )

        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO indexed_content_fts (rowid, url, title, content) VALUES (?, ?, ?, ?)",
            (row_id, url, title, text_content),
        )
        conn.execute(
            "INSERT INTO indexed_content_trigram (url, title, content) VALUES (?, ?, ?)",
            (url, title, text_content),
        )
        conn.commit()
        click.echo(f"Indexed: {title} ({url})")
