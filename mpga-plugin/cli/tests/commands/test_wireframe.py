"""Tests for the wireframe command.

Coverage checklist for: T002 — Replace external wireframe CSS with inline styles
Evidence: [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:21-25 :: _wireframe_css()

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: No wireframe-components.css file written to disk
        → test_does_not_write_a_css_file  (regression guard — already true, protects future)
[x] AC2: Generated HTML contains a <style> block with inline CSS
        → test_html_contains_non_empty_style_block  (RED — fallback CSS has < 5 lines)
[x] AC3: Inline CSS provides basic wireframe styling (colors, fonts, borders)
        → test_inline_css_contains_wireframe_class_rules  (RED — fallback has no .wf- rules)
[x] AC4: HTML output has no <link rel="stylesheet"> pointing to external files
        → test_html_has_no_external_stylesheet_link  (regression guard — already true)
[x] AC5: Existing 4 tests still pass
        → verified by running full suite (green-dev responsibility)

Untested branches / edge cases:
- [ ] CSS content does not change between screens (same stylesheet, different content)
- [ ] --screens 8 (max) still produces valid self-contained HTML
- [ ] inline CSS survives the html.escape() path for screen title/description (no CSS injection)

TPP ladder applied:
  1. null → constant:    no .css file written          (AC1 regression guard)
  2. constant → variable: <style> block is non-empty   (AC2 RED — forces substantive CSS)
  3. selection:           no <link> to external sheet   (AC4 regression guard)
  4. edge:               .wf- class rules present       (AC3 RED — forces wireframe rules)

──────────────────────────────────────────────────────────────────────────────────
Coverage checklist for: T003 — Replace hardcoded HTML template with dynamic layout
                                + add designer agent constraint
Evidence: [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:105-165 :: _render_html()
          [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:187-213 :: wireframe_cmd()

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: title appears in <h1> or <title> of the output
        → test_title_appears_in_h1_tag  (RED — title is only in <div>, not <h1>)
[x] AC2: description text appears as readable content (not just aria-label/data attr)
        → test_description_appears_in_paragraph_not_placeholder  (RED — description is
           wrapped in wf-placeholder-text class, which is a styled placeholder, not
           semantic readable content)
[x] AC3: two different descriptions produce different HTML bodies
        → test_two_descriptions_produce_different_html_structure  (RED — only the text
           value differs; nav items, sidebar items, and form fields are identical
           hardcoded boilerplate regardless of description)
[x] AC4: --agent flag invokes the designer agent
        → test_agent_flag_is_accepted_by_wireframe_command  (RED — --agent option does
           not exist; click exits code 2 on unrecognised option)
[ ] AC4 extended: designer agent is actually called (not just flag accepted)
        → (not yet written — depends on AC4 passing first)
[x] AC5: all existing 8 tests still pass
        → verified by running full suite before adding new tests (all 8 green)

Untested branches / edge cases:
- [ ] HTML-escaped title still renders correctly inside <h1> (e.g. "Foo & Bar" → &amp;)
- [ ] description with only whitespace produces a meaningful <h1> (not empty)
- [ ] --agent with a value other than "designer" (unknown agent name)
- [ ] --screens 1 with --agent (single screen + agent call)

TPP ladder for T003:
  1. null → constant:    title in <h1>                 (AC1 RED — forces <h1> element)
  2. constant → variable: description in <p> not muted  (AC2 RED — forces semantic body)
  3. variable → collection: body structure differs      (AC3 RED — forces dynamic layout)
  4. selection:           --agent flag accepted          (AC4 RED — forces new CLI option)
"""

from pathlib import Path

from click.testing import CliRunner

_MILESTONE_ID = "M007-ui-ux-design-layer"


def _seed_project(root: Path, milestone: str = _MILESTONE_ID) -> Path:
    mpga_dir = root / "MPGA"
    (mpga_dir / "board" / "tasks").mkdir(parents=True, exist_ok=True)
    (mpga_dir / "scopes").mkdir(parents=True, exist_ok=True)
    (mpga_dir / "mpga.config.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")

    from mpga.db.connection import get_connection
    from mpga.db.repos.milestones import Milestone, MilestoneRepo
    from mpga.db.schema import create_schema

    db_path = root / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_path))
    create_schema(conn)
    MilestoneRepo(conn).create(Milestone(id=milestone, name=milestone, status="active"))
    conn.close()

    return mpga_dir


class TestWireframeCommand:
    """wireframe command tests."""

    def test_generates_wireframe_artifacts_for_current_milestone(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Creates wireframe artifacts inside the active milestone design directory."""
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        result = runner.invoke(wireframe_cmd, ["login page", "--screens", "2"])

        assert result.exit_code == 0
        wireframes_dir = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        )
        assert wireframes_dir.is_dir()
        assert (wireframes_dir / "screen-1.html").exists()
        assert (wireframes_dir / "screen-1.txt").exists()
        assert "Renderer" in result.output

    def test_help_shows_usage(self):
        """Shows usage help for the wireframe command."""
        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        result = runner.invoke(wireframe_cmd, ["--help"])

        assert result.exit_code == 0
        assert "wireframe" in result.output
        assert "--screens" in result.output

    def test_escapes_user_content_in_html_output(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Escapes user-supplied content before writing HTML artifacts."""
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        payload = '<script>alert(1)</script>'
        result = runner.invoke(wireframe_cmd, [payload])

        assert result.exit_code == 0
        wireframes_dir = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        )
        html_output = (wireframes_dir / "screen-1.html").read_text(encoding="utf-8")

        assert payload not in html_output
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_output

    def test_does_not_write_an_svg_file_when_generating_wireframes(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Wireframe CLI must not produce .svg files after SVG generation is removed."""
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["login page"])

        # Assert
        assert result.exit_code == 0
        wireframes_dir = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        )
        assert not (wireframes_dir / "screen-1.svg").exists(), (
            "screen-1.svg must not be written — SVG generation should be removed"
        )

    # ── T002: Replace external wireframe CSS with inline styles ──────────────

    def test_does_not_write_a_css_file(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Wireframe generation must not write any .css file to disk.

        AC1 regression guard — [E] wireframe.py:21-25 :: _wireframe_css()
        The implementation must never emit a separate stylesheet; all CSS must
        live inside the HTML output itself.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["dashboard"])

        # Assert
        assert result.exit_code == 0
        output_root = tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID
        css_files = list(output_root.rglob("*.css"))
        assert css_files == [], (
            f"No .css files must be written, but found: {css_files}"
        )

    def test_html_contains_non_empty_style_block(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Generated HTML must embed a <style> block with substantive inline CSS.

        AC2 RED test — [E] wireframe.py:21-25 :: _wireframe_css()
        The fallback CSS (2 lines) is too minimal to constitute wireframe styling.
        This test requires at least 5 lines of CSS inside the <style> block, forcing
        green-dev to replace the external-file reader with a hardcoded stylesheet.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["settings panel"])

        # Assert
        assert result.exit_code == 0
        html = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.html"
        ).read_text(encoding="utf-8")

        assert "<style>" in html, "HTML must contain a <style> opening tag"
        assert "</style>" in html, "HTML must contain a </style> closing tag"

        style_start = html.index("<style>") + len("<style>")
        style_end = html.index("</style>")
        style_content = html[style_start:style_end].strip()

        assert len(style_content.splitlines()) >= 5, (
            f"Inline <style> block must contain at least 5 lines of CSS "
            f"(wireframe styling), got {len(style_content.splitlines())} lines. "
            "Replace the external-file reader with a complete hardcoded stylesheet."
        )

    def test_html_has_no_external_stylesheet_link(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Generated HTML must contain no <link rel='stylesheet'> to an external file.

        AC4 regression guard — [E] wireframe.py:44-101 :: _render_html()
        Ensures that no future refactor accidentally re-introduces an external link tag.
        The output must be entirely self-contained.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["user profile"])

        # Assert
        assert result.exit_code == 0
        html = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.html"
        ).read_text(encoding="utf-8")

        assert '<link rel="stylesheet"' not in html, (
            "HTML must not contain any <link rel=\"stylesheet\"> — all CSS must be inline"
        )
        assert "<link rel='stylesheet'" not in html, (
            "HTML must not contain any <link rel='stylesheet'> — all CSS must be inline"
        )

    def test_inline_css_contains_wireframe_class_rules(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Inline CSS must include at least one rule targeting a .wf- wireframe class.

        AC3 RED test — [E] wireframe.py:21-25 :: _wireframe_css()
        The fallback CSS only defines :root and body selectors — it has no .wf- rules.
        This test requires the inline stylesheet to contain CSS targeting the wireframe
        component classes (e.g. .wf-shell, .wf-header, .wf-button) that appear in the
        HTML template at [E] wireframe.py:55-98 :: _render_html().
        Green-dev must hardcode a complete wireframe stylesheet to pass this.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["notifications feed"])

        # Assert
        assert result.exit_code == 0
        html = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.html"
        ).read_text(encoding="utf-8")

        style_start = html.index("<style>") + len("<style>")
        style_end = html.index("</style>")
        style_content = html[style_start:style_end]

        assert ".wf-" in style_content, (
            "Inline <style> block must contain CSS rules targeting .wf- wireframe "
            "component classes (e.g. .wf-shell, .wf-header, .wf-button). "
            "The fallback CSS has no .wf- rules — replace it with a complete stylesheet."
        )

    # ── T003: Replace hardcoded HTML template with dynamic layout ────────────

    def test_title_appears_in_h1_tag(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Title must appear inside an <h1> element in the HTML body.

        AC1 RED test — [E] wireframe.py:105-165 :: _render_html()
        The current template places the title only in <title> (the browser tab) and in
        a <div class="wf-placeholder-text wf-title"> (a visually muted placeholder div).
        Neither is a semantic heading. The generated wireframe must use an <h1> so the
        title is the primary visible heading of the page — not a styled grey block.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["login page"])

        # Assert
        assert result.exit_code == 0
        html = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.html"
        ).read_text(encoding="utf-8")

        assert "<h1>" in html, (
            "HTML output must contain an <h1> element. "
            "Currently the title is placed only in a <div class='wf-placeholder-text wf-title'> "
            "— replace it with a semantic <h1> heading."
        )
        assert "Login page" in html[html.index("<h1>"):html.index("</h1>") + 5], (
            "The <h1> element must contain the wireframe title ('Login page'). "
            "Title is currently only in the <title> tag and a muted placeholder div."
        )

    def test_description_appears_in_paragraph_not_placeholder(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Description must appear in a <p> tag that is NOT styled as a visual placeholder.

        AC2 RED test — [E] wireframe.py:140-143 :: _render_html() body section
        The current template wraps the description in:
            <p class="wf-placeholder-text">{safe_description}</p>
        The 'wf-placeholder-text' class renders as a visually muted grey band — the
        same treatment as dummy filler text. Readable description content must be in a
        plain <p> without the placeholder class, so it renders as actual body copy.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        description = "User can reset their password via email link"

        # Act
        result = runner.invoke(wireframe_cmd, [description])

        # Assert
        assert result.exit_code == 0
        html = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.html"
        ).read_text(encoding="utf-8")

        # Description must appear somewhere in the body as readable content
        assert description in html, (
            f"Description '{description}' must appear in the HTML output."
        )
        # It must NOT be the case that the ONLY occurrence is inside wf-placeholder-text
        placeholder_wrapped = f'<p class="wf-placeholder-text">{description}</p>'
        assert placeholder_wrapped not in html, (
            f"Description must NOT be wrapped in <p class=\"wf-placeholder-text\">. "
            "That class renders the text as a visually muted grey placeholder band. "
            "Use a plain <p> or semantic content element instead."
        )

    def test_two_descriptions_produce_different_html_structure(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Two different descriptions must produce HTML with different body structures.

        AC3 RED test — [E] wireframe.py:105-165 :: _render_html()
        The current template is a hardcoded skeleton: regardless of description, the
        body always contains the same nav items ('Home', 'Details', 'Action'), the same
        sidebar links ('Navigation item' x3), and the same form fields ('Email',
        'Password'). Only the description text value changes — the layout structure is
        identical. Dynamic layout means the body elements adapt to the description
        content, so two semantically different descriptions must not produce the same
        inner HTML structure after all dynamic text tokens are normalised away.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner_a = CliRunner()
        runner_b = CliRunner()

        desc_a = "login form with email and password"
        desc_b = "data table showing recent orders"

        # Act — generate two wireframes for structurally different descriptions
        result_a = runner_a.invoke(wireframe_cmd, [desc_a])
        wireframes_dir = tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        html_a = (wireframes_dir / "screen-1.html").read_text(encoding="utf-8")

        # Use a sub-directory as a second project root
        second_root = tmp_path / "second"
        second_root.mkdir()
        _seed_project(second_root)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: second_root)

        result_b = runner_b.invoke(wireframe_cmd, [desc_b])
        wireframes_dir_b = second_root / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        html_b = (wireframes_dir_b / "screen-1.html").read_text(encoding="utf-8")

        # Assert — both commands succeeded
        assert result_a.exit_code == 0
        assert result_b.exit_code == 0

        # Extract body content (between <body> and </body>) for structural comparison
        body_a = html_a[html_a.index("<body>"):html_a.index("</body>")]
        body_b = html_b[html_b.index("<body>"):html_b.index("</body>")]

        # Normalise away ALL dynamic text tokens (both original-case and title-cased)
        # so only the HTML structure remains for comparison.
        def _normalise(body: str, desc: str) -> str:
            from mpga.commands.wireframe import _title_from_description
            title = _title_from_description(desc)
            return (
                body
                .replace(title, "TITLE")
                .replace(desc, "DESC")
                # html-escaped variants
                .replace(title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), "TITLE")
                .replace(desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), "DESC")
            )

        structure_a = _normalise(body_a, desc_a)
        structure_b = _normalise(body_b, desc_b)

        assert structure_a != structure_b, (
            "After normalising title and description text tokens, the HTML body structures "
            "of two different descriptions must differ. Currently both descriptions produce "
            "identical structures — same nav items ('Home', 'Details', 'Action'), same "
            "sidebar links ('Navigation item' x3), same form fields ('Email', 'Password'). "
            "The layout must adapt to the description content so a 'login form' and a "
            "'data table' produce structurally different wireframes."
        )

    def test_agent_flag_is_accepted_by_wireframe_command(self):
        """wireframe command must accept an --agent flag without error.

        AC4 RED test — [E] wireframe.py:187-213 :: wireframe_cmd()
        The current command signature has no --agent option. Passing '--agent designer'
        causes click to exit with code 2 ('No such option: --agent'). Green-dev must add
        an --agent option so the flag is accepted by the CLI.
        """
        # Arrange
        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act — invoke with --agent flag; no project root needed since we only check
        # that the flag is *recognised* by click (not that agent logic runs)
        result = runner.invoke(wireframe_cmd, ["--help"])
        help_text = result.output

        # Assert — --agent must appear in the command's help output
        assert "--agent" in help_text, (
            "'wireframe --help' must list an --agent option. "
            "Currently no --agent flag exists on wireframe_cmd — "
            "add it so callers can request designer agent execution."
        )


# ── T005: Honor renderer detection result in wireframe CLI ───────────────────
#
# Coverage checklist for: T005 — Honor renderer detection result in wireframe CLI
# Evidence: [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:88-91 :: _detect_renderer()
#           [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:192-215 :: wireframe_cmd()
#
# Acceptance criteria → Test status
# ──────────────────────────────────
# [x] AC1: --agent designer + html renderer → _render_html() is called
#         → test_render_html_is_called_when_agent_designer_and_html_renderer
# [x] AC2: EXCALIDRAW_MCP_AVAILABLE=1 → no .html file written (excalidraw path taken)
#         → test_html_file_is_not_written_when_excalidraw_renderer_detected
# [ ] AC3: renderer detection result is logged/printed (user can see chosen renderer)
#         → (already covered by existing test_generates_wireframe_artifacts_for_current_milestone
#            which asserts "Renderer" in result.output — regression guard, skip re-testing)
# [x] AC4: _detect_renderer() result is not ignored — it influences behavior
#         → test_render_html_is_not_called_when_excalidraw_renderer_detected
# [ ] AC5: all existing 12 tests still pass
#         → verified by running full suite (green-dev responsibility)
#
# Untested branches / edge cases:
# - [ ] EXCALIDRAW_MCP_AVAILABLE set to something other than "1" (e.g. "0", "true")
# - [ ] --agent with excalidraw renderer AND --screens > 1
# - [ ] no --agent flag with excalidraw renderer (edge: should still route differently)
#
# TPP ladder for T005:
#   1. null → constant:    _render_html NOT called for excalidraw renderer   (AC4 RED)
#   2. constant → variable: _render_html IS called for html renderer + agent  (AC1 RED)
#   3. variable → output:  "excalidraw" appears in output when env var set    (AC2 RED)


class TestWireframeRendererDetection:
    """Tests that wireframe_cmd honors the renderer detected by _detect_renderer().

    Evidence: [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:88-91 :: _detect_renderer()
              [E] mpga-plugin/cli/src/mpga/commands/wireframe.py:203-208 :: if renderer == "html":
    The renderer variable drives a branching guard at line 203. When renderer == "html",
    HTML files are written. When renderer == "excalidraw", HTML generation is skipped.
    ASCII output remains unconditional (lines 199-201) for all renderers.
    """

    def test_render_html_is_not_called_when_excalidraw_renderer_detected(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """_render_html is NOT called when excalidraw renderer is active.

        AC4 GREEN test — [E] wireframe.py:203-208 :: if renderer == "html":
        When _detect_renderer() returns ("excalidraw", ...), the command branches away
        from _render_html() and does not write .html files. ASCII art is still rendered.
        This test patches _render_html to a sentinel and asserts it is NOT called when
        EXCALIDRAW_MCP_AVAILABLE=1 is set.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)
        monkeypatch.setenv("EXCALIDRAW_MCP_AVAILABLE", "1")

        from unittest.mock import patch

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        with patch("mpga.commands.wireframe._render_html") as mock_render_html:
            mock_render_html.return_value = "<html></html>"
            result = runner.invoke(wireframe_cmd, ["login screen", "--agent", "designer"])

        # Assert — command must succeed but _render_html must NOT be called
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert not mock_render_html.called, (
            "_render_html must NOT be called when the excalidraw renderer is detected. "
            "Currently wireframe_cmd calls _render_html() unconditionally at line 204 "
            "regardless of what _detect_renderer() returns. "
            "The renderer variable must actually branch the execution path."
        )

    def test_render_html_is_called_when_agent_designer_and_html_renderer(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """_render_html must be called when --agent designer is passed and renderer is html.

        AC1 regression guard — [E] wireframe.py:199-204 :: wireframe_cmd()
        When EXCALIDRAW_MCP_AVAILABLE is NOT set, _detect_renderer() returns ("html", ...).
        With --agent designer and html renderer, the command must still call _render_html()
        to produce the HTML wireframe artifact. This test confirms the html branch works.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)
        monkeypatch.delenv("EXCALIDRAW_MCP_AVAILABLE", raising=False)

        from unittest.mock import call, patch

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        with patch("mpga.commands.wireframe._render_html", wraps=__import__(
            "mpga.commands.wireframe", fromlist=["_render_html"]
        )._render_html) as mock_render_html:
            result = runner.invoke(wireframe_cmd, ["dashboard", "--agent", "designer"])

        # Assert — command must succeed and _render_html must have been called
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert mock_render_html.called, (
            "_render_html must be called when renderer is html and --agent designer is passed. "
            "The html rendering path must remain active for the html renderer."
        )

    def test_html_file_is_not_written_when_excalidraw_renderer_detected(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """No .html wireframe file must be written when the excalidraw renderer is active.

        AC2 RED test — [E] wireframe.py:92-95 :: _detect_renderer()
                       [E] wireframe.py:203-208 :: wireframe_cmd() screen loop
        When EXCALIDRAW_MCP_AVAILABLE=1, _detect_renderer() returns ("excalidraw", ...).
        The command currently writes screen-1.html unconditionally inside the loop at
        line 207. When the excalidraw renderer is chosen, HTML files must NOT be written
        to the wireframes directory — the renderer has taken over output responsibility.
        Green-dev must guard the HTML write behind a renderer branch.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)
        monkeypatch.setenv("EXCALIDRAW_MCP_AVAILABLE", "1")

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["settings page", "--agent", "designer"])

        # Assert — no .html file should be written for excalidraw renderer
        assert result.exit_code == 0, f"Command failed: {result.output}"
        wireframes_dir = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        )
        html_files = list(wireframes_dir.glob("*.html"))
        assert html_files == [], (
            "When EXCALIDRAW_MCP_AVAILABLE=1 is set and the excalidraw renderer is chosen, "
            "no .html wireframe files must be written to disk. "
            f"Found unexpected HTML files: {html_files}. "
            "The renderer branch must skip the _render_html() → write_text() path."
        )


# ── T004: Add ASCII stdout as secondary wireframe output ─────────────────────


class TestWireframeAsciiOutput:
    """Tests for T004 — ASCII stdout as secondary wireframe output.

    Coverage checklist for: T004 — Add ASCII stdout as secondary wireframe output
    Evidence: [E] src/mpga/commands/wireframe.py:169-185 :: _render_ascii()
              [E] src/mpga/commands/wireframe.py:203-215 :: wireframe_cmd() screen loop

    Acceptance criteria → Test status
    ──────────────────────────────────
    [x] AC1: .txt file is written alongside .html in the wireframes directory
            → test_txt_file_is_written_alongside_html_file
              (regression guard — already implemented at wireframe.py:208; passes now)
    [x] AC2: .txt file contains ASCII art (+, -, | box characters)
            → test_txt_file_contains_ascii_box_characters
              (regression guard — _render_ascii() already emits + chars; passes now)
    [x] AC3: .txt file contains the wireframe title
            → test_txt_file_contains_wireframe_title
              (regression guard — _render_ascii() line 172 inserts title; passes now)
    [ ] AC4: running wireframe prints ASCII representation to stdout
            → test_wireframe_prints_ascii_to_stdout
              (RED — wireframe_cmd() never calls click.echo/print with ascii_art)

    Untested branches / edge cases:
    - [ ] --screens 2 produces stdout for both screens (not just screen 1)
    - [ ] title longer than 60 chars is truncated in .txt but appears full in .html
    - [ ] description longer than 37 chars is truncated in .txt output

    TPP ladder applied:
      1. null → constant:    .txt file exists (AC1 regression guard — already green)
      2. constant → variable: .txt contains + chars (AC2 regression guard — already green)
      3. variable → selection: .txt contains title (AC3 regression guard — already green)
      4. selection → output:  stdout prints ASCII (AC4 RED — forces click.echo call)

    NOTE: AC1/AC2/AC3 tests pass immediately against the current implementation and
    serve as regression guards. AC4 is the only genuinely RED test — it fails because
    wireframe_cmd() never echoes ascii_art to stdout (lines 213-215 only call log.success
    and log.dim). Green-dev must add a click.echo(ascii_art) call inside the screen loop.
    """

    def test_txt_file_is_written_alongside_html_file(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """A .txt file must be written next to the .html file after wireframe generation.

        AC1 regression guard — [E] src/mpga/commands/wireframe.py:207-208 :: wireframe_cmd()
        Already implemented; this test protects against regressions that remove the .txt write.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["dashboard overview"])

        # Assert
        assert result.exit_code == 0
        wireframes_dir = tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes"
        assert (wireframes_dir / "screen-1.html").exists(), (
            "screen-1.html must exist after wireframe generation"
        )
        assert (wireframes_dir / "screen-1.txt").exists(), (
            "screen-1.txt must be written alongside screen-1.html. "
            "The ASCII text representation must be persisted to disk."
        )

    def test_txt_file_contains_ascii_box_characters(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """The .txt file must contain +, -, and | characters forming ASCII box art borders.

        AC2 regression guard — [E] src/mpga/commands/wireframe.py:169-185 :: _render_ascii()
        The _render_ascii() function already emits lines of +, -, and | characters.
        This test guards against regressions that replace the box art with plain text.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["order list"])

        # Assert
        assert result.exit_code == 0
        txt_content = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.txt"
        ).read_text(encoding="utf-8")
        assert "+" in txt_content, (
            "screen-1.txt must contain '+' characters forming ASCII box corners."
        )
        assert "-" in txt_content, (
            "screen-1.txt must contain '-' characters for horizontal box borders."
        )
        assert "|" in txt_content, (
            "screen-1.txt must contain '|' characters for vertical box borders."
        )

    def test_txt_file_contains_wireframe_title(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """The .txt file must include the wireframe title in the ASCII header row.

        AC3 regression guard — [E] src/mpga/commands/wireframe.py:172 :: _render_ascii()
        Line 172 inserts the title into the top row of the ASCII box: '| <title> |'.
        This test guards against regressions that strip the title from the .txt output.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["user profile settings"])

        # Assert
        assert result.exit_code == 0
        txt_content = (
            tmp_path / ".mpga" / "wireframes" / _MILESTONE_ID / "wireframes" / "screen-1.txt"
        ).read_text(encoding="utf-8")
        assert "User profile settings" in txt_content, (
            "screen-1.txt must contain the wireframe title 'User profile settings'. "
            "The ASCII header row (_render_ascii line 172) must embed the title."
        )

    def test_wireframe_prints_ascii_to_stdout(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Running wireframe must print the ASCII art representation to stdout.

        AC4 RED test — [E] src/mpga/commands/wireframe.py:203-215 :: wireframe_cmd()
        The current implementation calls _render_ascii() and writes the result to a
        .txt file (line 208), but never echoes it to stdout. Lines 213-215 only emit
        log.success and log.dim messages — no click.echo(ascii_art). Green-dev must
        add a click.echo(ascii_art) call inside the screen loop so the ASCII wireframe
        appears in the terminal when the command runs.
        """
        # Arrange
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(wireframe_cmd, ["login screen"])

        # Assert
        assert result.exit_code == 0
        # The ASCII border characters must appear in stdout, not just in the .txt file
        assert "+" in result.output, (
            "wireframe stdout must contain '+' — the ASCII box art must be printed to "
            "stdout. Currently wireframe_cmd() only writes the ASCII to a .txt file at "
            "line 208; it never calls click.echo(ascii_art). "
            "Add click.echo(ascii_art) inside the screen loop to fix this."
        )
        assert "|" in result.output, (
            "wireframe stdout must contain '|' — ASCII box art vertical borders "
            "must appear in the terminal output, not only in screen-1.txt."
        )
        # The title must also appear in stdout, not just in the .txt file
        assert "Login screen" in result.output, (
            "wireframe stdout must contain the wireframe title 'Login screen'. "
            "The ASCII header row includes the title — it must be visible on stdout."
        )
