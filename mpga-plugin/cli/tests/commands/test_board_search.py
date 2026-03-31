"""Tests for board search functionality."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_board_with_tasks(tmp_path: Path, monkeypatch) -> Path:
    """Set up a board with varied tasks for search testing."""
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    from mpga.board.board import AddTaskOptions, add_task, create_empty_board, save_board
    from mpga.board.task import parse_task_file, render_task_file

    board = create_empty_board()
    save_board(str(board_dir), board)

    t1 = add_task(board, str(tasks_dir), AddTaskOptions(
        title="Fix critical login bug",
        column="todo",
        priority="critical",
        scopes=["auth"],
        tags=["bugfix", "urgent"],
    ))
    t2 = add_task(board, str(tasks_dir), AddTaskOptions(
        title="Add unit tests for parser",
        column="in-progress",
        priority="high",
        scopes=["core"],
        tags=["testing"],
    ))
    add_task(board, str(tasks_dir), AddTaskOptions(
        title="Refactor board layout",
        column="backlog",
        priority="medium",
        scopes=["board"],
        tags=["refactor"],
    ))
    add_task(board, str(tasks_dir), AddTaskOptions(
        title="Update documentation",
        column="done",
        priority="low",
        scopes=["docs"],
        tags=["docs"],
    ))
    save_board(str(board_dir), board)

    # Assign agents to some tasks
    t2_file = next(f for f in tasks_dir.iterdir() if f.name.startswith(t2.id))
    t2_task = parse_task_file(str(t2_file))
    t2_task.assigned = "green-dev"
    t2_file.write_text(render_task_file(t2_task))

    t1_file = next(f for f in tasks_dir.iterdir() if f.name.startswith(t1.id))
    t1_task = parse_task_file(str(t1_file))
    t1_task.assigned = "red-dev"
    t1_file.write_text(render_task_file(t1_task))

    monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
    monkeypatch.setattr("mpga.commands.board_db.find_project_root", lambda: tmp_path)

    return board_dir


def mirror_board_into_sqlite(board_dir: Path) -> None:
    """Populate the SQLite board mirror from board/task files."""
    from mpga.commands.board_handlers import _refresh_sqlite_board_mirror

    _refresh_sqlite_board_mirror(str(board_dir), str(board_dir / "tasks"))


# ---------------------------------------------------------------------------
# Tests: board search
# ---------------------------------------------------------------------------

class TestBoardSearch:
    """board search tests."""

    def test_returns_all_tasks_no_filters(self, tmp_path: Path, monkeypatch):
        """Returns all tasks when no filters are provided."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import handle_board_search

        results = handle_board_search("")
        assert len(results) == 4

    def test_filters_by_priority(self, tmp_path: Path, monkeypatch):
        """Filters tasks by priority."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("", filters=BoardSearchFilters(priority="critical"))
        assert len(results) == 1
        assert results[0].id == "T001"

    def test_filters_by_column(self, tmp_path: Path, monkeypatch):
        """Filters tasks by column."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("", filters=BoardSearchFilters(column="in-progress"))
        assert len(results) == 1
        assert "parser" in results[0].title

    def test_filters_by_scope(self, tmp_path: Path, monkeypatch):
        """Filters tasks by scope."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("", filters=BoardSearchFilters(scope="auth"))
        assert len(results) == 1
        assert "login" in results[0].title

    def test_filters_by_assigned_agent(self, tmp_path: Path, monkeypatch):
        """Filters tasks by assigned agent."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("", filters=BoardSearchFilters(agent="green-dev"))
        assert len(results) == 1
        assert "parser" in results[0].title

    def test_filters_by_tags(self, tmp_path: Path, monkeypatch):
        """Filters tasks by tags."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("", filters=BoardSearchFilters(tags="bugfix"))
        assert len(results) == 1
        assert "login" in results[0].title

    def test_searches_task_titles(self, tmp_path: Path, monkeypatch):
        """Searches task titles with text query."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import handle_board_search

        results = handle_board_search("board")
        assert len(results) == 1
        assert "board" in results[0].title.lower()

    def test_case_insensitive_search(self, tmp_path: Path, monkeypatch):
        """Case-insensitive text search."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import handle_board_search

        results = handle_board_search("LOGIN")
        assert len(results) == 1
        assert "login" in results[0].title

    def test_combines_text_and_filter(self, tmp_path: Path, monkeypatch):
        """Combines text query with filter options."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("test", filters=BoardSearchFilters(priority="high"))
        assert len(results) == 1
        assert "parser" in results[0].title

    def test_returns_empty_when_no_match(self, tmp_path: Path, monkeypatch):
        """Returns empty array when no tasks match."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("nonexistent", filters=BoardSearchFilters(priority="critical"))
        assert len(results) == 0

    def test_supports_multiple_tags(self, tmp_path: Path, monkeypatch):
        """Supports multiple tag matching (comma-separated)."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        results = handle_board_search("", filters=BoardSearchFilters(tags="bugfix,urgent"))
        assert len(results) == 1
        assert "bugfix" in results[0].tags
        assert "urgent" in results[0].tags

    def test_prints_matching_tasks(self, tmp_path: Path, monkeypatch, capsys):
        """Prints matching tasks to console."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import handle_board_search

        handle_board_search("login")
        output = capsys.readouterr().out
        assert "T001" in output
        assert "login" in output

    def test_prints_no_results_message(self, tmp_path: Path, monkeypatch, capsys):
        """Prints a message when no results found."""
        setup_board_with_tasks(tmp_path, monkeypatch)
        from mpga.commands.board_handlers import handle_board_search

        handle_board_search("zzz-no-match-zzz")
        output = capsys.readouterr().out
        assert "No tasks match" in output

    def test_search_uses_sqlite_fts_body_matches(self, tmp_path: Path, monkeypatch):
        """Uses the SQLite mirror so body-only matches are searchable."""
        board_dir = setup_board_with_tasks(tmp_path, monkeypatch)
        task_path = board_dir / "tasks" / "T003-refactor-board-layout.md"
        content = task_path.read_text(encoding="utf-8")
        content += "\nThis task prepares the SQLite mirror migration.\n"
        task_path.write_text(content, encoding="utf-8")
        mirror_board_into_sqlite(board_dir)

        from mpga.commands.board_handlers import handle_board_search

        results = handle_board_search("sqlite")
        assert len(results) == 1
        assert results[0].id == "T003"

    def test_prints_compressed_results_when_sqlite_is_available(self, tmp_path: Path, monkeypatch, capsys):
        """Prints compressed task summaries for DB-backed searches by default."""
        board_dir = setup_board_with_tasks(tmp_path, monkeypatch)
        mirror_board_into_sqlite(board_dir)

        from mpga.commands.board_handlers import handle_board_search

        handle_board_search("login")
        output = capsys.readouterr().out
        assert "T001 [todo] critical: Fix critical login bug" in output
        assert "@red-dev" not in output
