from __future__ import annotations

from html import escape
import os
from pathlib import Path

import click

from mpga.commands._shared import _current_milestone
from mpga.core.config import find_project_root
from mpga.core.logger import log


def _design_root(project_root: Path, milestone: str) -> Path:
    design_root = project_root / ".mpga" / "wireframes" / milestone
    for folder in ("wireframes", "prototypes", "components", "screenshots"):
        (design_root / folder).mkdir(parents=True, exist_ok=True)
    return design_root


def _wireframe_css() -> str:
    asset_path = Path(__file__).resolve().parents[4] / "assets" / "wireframe-components.css"
    if asset_path.exists():
        return asset_path.read_text(encoding="utf-8")
    return ":root { --color-border: #9ca3af; }\nbody { font-family: sans-serif; }\n"


def _detect_renderer() -> tuple[str, str]:
    if os.environ.get("EXCALIDRAW_MCP_AVAILABLE") == "1":
        return "excalidraw", "Excalidraw MCP detected"
    return "html", "Excalidraw MCP not detected"


def _title_from_description(description: str) -> str:
    trimmed = description.strip()
    if not trimmed:
        return "Untitled wireframe"
    return trimmed[0].upper() + trimmed[1:]


def _render_html(title: str, description: str, css: str, screen_number: int, total_screens: int) -> str:
    safe_title = escape(title, quote=True)
    safe_description = escape(description, quote=True)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title} - screen {screen_number}</title>
    <style>
{css}
    </style>
  </head>
  <body>
    <main class="wf-shell" aria-label="Wireframe preview">
      <header class="wf-header">
        <div class="wf-placeholder-text wf-title">{safe_title}</div>
        <nav class="wf-nav" aria-label="Primary">
          <span class="wf-button">Home</span>
          <span class="wf-button">Details</span>
          <span class="wf-button">Action</span>
        </nav>
      </header>
      <section class="wf-grid wf-grid-2">
        <aside class="wf-sidebar">
          <div class="wf-tabs">
            <span class="wf-button">Overview</span>
            <span class="wf-button">Settings</span>
          </div>
          <ul class="wf-list" aria-label="Navigation">
            <li class="wf-placeholder-text">Navigation item</li>
            <li class="wf-placeholder-text">Navigation item</li>
            <li class="wf-placeholder-text">Navigation item</li>
          </ul>
        </aside>
        <section class="wf-card" aria-label="Main content">
          <div class="wf-placeholder-image" aria-hidden="true"></div>
          <p class="wf-placeholder-text">{safe_description}</p>
          <form class="wf-form" aria-label="Prototype form">
            <label class="wf-input">
              <span class="wf-placeholder-text">Email</span>
              <span class="wf-input-box"></span>
            </label>
            <label class="wf-input">
              <span class="wf-placeholder-text">Password</span>
              <span class="wf-input-box"></span>
            </label>
            <div class="wf-button-row">
              <span class="wf-button">Primary action</span>
              <span class="wf-button wf-button-secondary">Secondary action</span>
            </div>
          </form>
          <footer class="wf-footer">
            Screen {screen_number} of {total_screens}
          </footer>
        </section>
      </section>
    </main>
  </body>
</html>
"""


def _render_ascii(title: str, description: str, screen_number: int, total_screens: int) -> str:
    return "\n".join(
        [
            "+--------------------------------------------------------------+",
            f"| {title[:60]:<60} |",
            "+----------------------+---------------------------------------+",
            "| navigation           |                                       |",
            "| - overview           |           hero / form area            |",
            "| - settings           |                                       |",
            "| - reports            |                                       |",
            "|                      |                                       |",
            "|                      |                                       |",
            f"| screen {screen_number}/{total_screens:<12}| {description[:37]:<37} |",
            "+--------------------------------------------------------------+",
            "",
        ]
    )


@click.command("wireframe", help="Generate wireframe artifacts for the active milestone")
@click.argument("description")
@click.option("--screens", type=click.IntRange(1, 8), default=1, show_default=True)
def wireframe_cmd(description: str, screens: int) -> None:
    project_root = find_project_root() or Path.cwd()
    milestone = _current_milestone(project_root)
    design_root = _design_root(project_root, milestone)
    wireframes_dir = design_root / "wireframes"
    prototypes_dir = design_root / "prototypes"

    renderer, reason = _detect_renderer()
    title = _title_from_description(description)
    css = _wireframe_css()

    for screen_number in range(1, screens + 1):
        html = _render_html(title, description, css, screen_number, screens)
        ascii_art = _render_ascii(title, description, screen_number, screens)

        (wireframes_dir / f"screen-{screen_number}.html").write_text(html, encoding="utf-8")
        (wireframes_dir / f"screen-{screen_number}.txt").write_text(ascii_art, encoding="utf-8")

        if screen_number == 1:
            (prototypes_dir / "index.html").write_text(html, encoding="utf-8")

    log.success(f"Renderer: {renderer} ({reason})")
    log.success(f"Generated wireframes in {wireframes_dir}")
    log.dim(f"Active milestone: {milestone}")
