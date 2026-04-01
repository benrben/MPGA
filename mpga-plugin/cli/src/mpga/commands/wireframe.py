from __future__ import annotations

import os
from html import escape
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


_WIREFRAME_CSS = """\
:root {
  --wf-color-page: #f8fafc;
  --wf-color-panel: #ffffff;
  --wf-color-border: #94a3b8;
  --wf-color-muted: #e2e8f0;
  --wf-color-ink: #334155;
  --wf-color-soft: #64748b;
  --wf-space-1: 0.5rem;
  --wf-space-2: 0.75rem;
  --wf-space-3: 1rem;
  --wf-space-4: 1.5rem;
  --wf-space-5: 2rem;
  --wf-radius: 1rem;
  --wf-border: 2px dashed var(--wf-color-border);
  --wf-shadow: 0 16px 40px rgba(148, 163, 184, 0.18);
  --wf-font: "IBM Plex Sans", "Segoe UI", sans-serif;
  --wf-max-width: 80rem;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: linear-gradient(180deg, var(--wf-color-page), #eef2f7);
  color: var(--wf-color-ink);
  font-family: var(--wf-font);
}
.wf-shell, .wf-card, .wf-sidebar, .wf-modal, .wf-table, .wf-form,
.wf-nav, .wf-footer, .wf-grid, .wf-placeholder-image,
.wf-placeholder-text, .wf-button, .wf-input, .wf-list, .wf-tabs {
  border: var(--wf-border);
  border-radius: var(--wf-radius);
}
.wf-shell {
  max-width: var(--wf-max-width);
  margin: 0 auto;
  padding: var(--wf-space-5);
  display: grid;
  gap: var(--wf-space-4);
}
.wf-header, .wf-footer, .wf-nav, .wf-tabs, .wf-button-row {
  display: flex; flex-wrap: wrap; gap: var(--wf-space-2); align-items: center;
}
.wf-header, .wf-card, .wf-sidebar, .wf-modal, .wf-table, .wf-form, .wf-footer {
  background: var(--wf-color-panel);
  box-shadow: var(--wf-shadow);
  padding: var(--wf-space-4);
}
.wf-title { min-width: 12rem; min-height: 1.5rem; }
.wf-grid { display: grid; gap: var(--wf-space-4); padding: var(--wf-space-3); background: rgba(255,255,255,.55); }
.wf-grid-2 { grid-template-columns: minmax(14rem, 18rem) minmax(0, 1fr); }
.wf-sidebar, .wf-card { display: grid; gap: var(--wf-space-3); }
.wf-form, .wf-list { display: grid; gap: var(--wf-space-2); padding: var(--wf-space-3); }
.wf-table { min-height: 10rem; background-image: linear-gradient(var(--wf-color-muted) 1px, transparent 1px), linear-gradient(90deg, var(--wf-color-muted) 1px, transparent 1px); background-size: 100% 2.5rem, 12rem 100%; }
.wf-modal { min-height: 12rem; }
.wf-placeholder-image { min-height: 12rem; background: linear-gradient(135deg, rgba(203,213,225,.85), rgba(226,232,240,.7)); }
.wf-placeholder-text { min-height: 1rem; background: linear-gradient(90deg, rgba(226,232,240,.75), rgba(241,245,249,.95)); color: var(--wf-color-soft); padding: var(--wf-space-2); }
.wf-button, .wf-button-secondary { display: inline-flex; align-items: center; justify-content: center; min-width: 8rem; min-height: 2.75rem; padding: 0 var(--wf-space-3); background: var(--wf-color-muted); }
.wf-input { display: grid; gap: var(--wf-space-2); padding: var(--wf-space-2); }
.wf-input-box { display: block; min-height: 2.75rem; border: var(--wf-border); border-radius: calc(var(--wf-radius) - .375rem); background: rgba(255,255,255,.85); }
.wf-list { list-style: none; margin: 0; }
.wf-tabs { padding: var(--wf-space-2); }
@media (max-width: 47.99rem) { .wf-shell { padding: var(--wf-space-3); } .wf-grid-2 { grid-template-columns: 1fr; } }
@media (min-width: 48rem) { .wf-placeholder-image { min-height: 16rem; } }
@media (min-width: 80rem) { .wf-shell { padding: calc(var(--wf-space-5) + var(--wf-space-3)); } }
"""


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
    <main class="wf-shell" aria-label="Wireframe preview" data-wf-desc-len="{len(description)}">
      <header class="wf-header">
        <h1>{safe_title}</h1>
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
          <p class="wf-description">{safe_description}</p>
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
@click.option("--agent", default=None, help="Agent to invoke (e.g. designer).")
def wireframe_cmd(description: str, screens: int, agent: str | None) -> None:
    project_root = find_project_root() or Path.cwd()
    milestone = _current_milestone(project_root)
    design_root = _design_root(project_root, milestone)
    wireframes_dir = design_root / "wireframes"
    prototypes_dir = design_root / "prototypes"

    renderer, reason = _detect_renderer()
    title = _title_from_description(description)

    for screen_number in range(1, screens + 1):
        ascii_art = _render_ascii(title, description, screen_number, screens)
        (wireframes_dir / f"screen-{screen_number}.txt").write_text(ascii_art, encoding="utf-8")
        click.echo(ascii_art)

        if renderer == "html":
            html = _render_html(title, description, _WIREFRAME_CSS, screen_number, screens)
            (wireframes_dir / f"screen-{screen_number}.html").write_text(html, encoding="utf-8")

            if screen_number == 1:
                (prototypes_dir / "index.html").write_text(html, encoding="utf-8")

    log.success(f"Renderer: {renderer} ({reason})")
    log.success(f"Generated wireframes in {wireframes_dir}")
    log.dim(f"Active milestone: {milestone}")
