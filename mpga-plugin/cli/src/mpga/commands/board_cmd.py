"""Click group for the ``mpga board`` command tree.

Mirrors the Commander-based board.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

import click

from mpga.commands import board_handlers as h
from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search


@click.group("board", help="The GREATEST task board ever built")
def board() -> None:
    pass


# -- live -------------------------------------------------------------------

@board.command("live", help="Persist the board to the SQLite mirror -- FAST and RELIABLE")
def board_live() -> None:
    h.handle_board_live()


# -- show -------------------------------------------------------------------

@board.command("show", help="Display the GREATEST board you've ever seen")
@click.option("--json", "json_output", is_flag=True, default=False, help="Machine-readable output")
@click.option("--milestone", default=None, help="Specific milestone board")
@click.option("--full", is_flag=True, default=False, help="Show the full board instead of the compressed summary")
def board_show(json_output: bool, milestone: str | None, full: bool) -> None:
    h.handle_board_show(json_output=json_output, milestone=milestone, full=full)


# -- add --------------------------------------------------------------------

@board.command("add", help="Create a new task -- it's going to be GREAT")
@click.argument("title")
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"], case_sensitive=False),
    default="medium",
    help="Task priority",
)
@click.option("--scope", default=None, help="Link to scope document")
@click.option("--depends", default=None, help="Add dependency (comma-separated)")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option(
    "--column",
    type=click.Choice(["backlog", "todo", "in-progress", "testing", "review", "done"], case_sensitive=False),
    default="backlog",
    help="Initial column",
)
@click.option("--milestone", default=None, help="Link to milestone")
def board_add(
    title: str,
    priority: str,
    scope: str | None,
    depends: str | None,
    tags: str | None,
    column: str,
    milestone: str | None,
) -> None:
    h.handle_board_add(
        title,
        priority=priority,
        scope=scope,
        depends=depends,
        tags=tags,
        column=column,
        milestone=milestone,
    )


# -- move -------------------------------------------------------------------

@board.command("move", help="Move task between columns -- FAST, like a WINNER")
@click.argument("task_id")
@click.argument("column")
@click.option("--force", is_flag=True, default=False, help="Ignore WIP limits")
def board_move(task_id: str, column: str, force: bool) -> None:
    h.handle_board_move(task_id, column, force=force)


# -- claim ------------------------------------------------------------------

@board.command("claim", help="Agent claims a task -- CLAIMED, like a CHAMPION")
@click.argument("task_id")
@click.option("--agent", default=None, help="Agent name")
@click.option("--force", is_flag=True, default=False, help="Ignore WIP limits")
def board_claim(task_id: str, agent: str | None, force: bool) -> None:
    h.handle_board_claim(task_id, agent=agent, force=force)


# -- assign -----------------------------------------------------------------

@board.command("assign", help='Assign task to the BEST agent or a "human"')
@click.argument("task_id")
@click.argument("agent")
def board_assign(task_id: str, agent: str) -> None:
    h.handle_board_assign(task_id, agent)


# -- update -----------------------------------------------------------------

@board.command("update", help="Update task fields -- make them PERFECT")
@click.argument("task_id")
@click.option(
    "--status",
    type=click.Choice(["blocked", "stale", "rework", "paused"], case_sensitive=False),
    default=None,
    help="Task status",
)
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"], case_sensitive=False),
    default=None,
    help="Task priority",
)
@click.option("--evidence-add", default=None, help="Record produced evidence link")
@click.option(
    "--tdd-stage",
    type=click.Choice(["green", "red", "blue", "review", "done"], case_sensitive=False),
    default=None,
    help="TDD stage",
)
def board_update(
    task_id: str,
    status: str | None,
    priority: str | None,
    evidence_add: str | None,
    tdd_stage: str | None,
) -> None:
    h.handle_board_update(
        task_id,
        status=status,
        priority=priority,
        evidence_add=evidence_add,
        tdd_stage=tdd_stage,
    )


# -- block ------------------------------------------------------------------

@board.command("block", help="Mark task as blocked -- SAD but necessary")
@click.argument("task_id")
@click.argument("reason")
def board_block(task_id: str, reason: str) -> None:
    h.handle_board_block(task_id, reason)


# -- unblock ----------------------------------------------------------------

@board.command("unblock", help="UNBLOCK task -- back in action, TREMENDOUS")
@click.argument("task_id")
def board_unblock(task_id: str) -> None:
    h.handle_board_unblock(task_id)


# -- deps -------------------------------------------------------------------

@board.command("deps", help="Show the BEAUTIFUL dependency tree")
@click.argument("task_id")
def board_deps(task_id: str) -> None:
    h.handle_board_deps(task_id)


# -- stats ------------------------------------------------------------------

@board.command("stats", help="Board statistics -- the BEST numbers")
def board_stats() -> None:
    h.handle_board_stats()


# -- archive ----------------------------------------------------------------

@board.command("archive", help="Archive the WINNING tasks to milestone -- VICTORY LAP")
def board_archive() -> None:
    h.handle_board_archive()


# -- search -----------------------------------------------------------------

@board.command("search", help="Search and filter tasks -- we find EVERYTHING")
@click.argument("query", default="")
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"], case_sensitive=False),
    default=None,
    help="Filter by priority",
)
@click.option(
    "--column",
    type=click.Choice(["backlog", "todo", "in-progress", "testing", "review", "done"], case_sensitive=False),
    default=None,
    help="Filter by column",
)
@click.option("--scope", default=None, help="Filter by scope")
@click.option("--agent", default=None, help="Filter by assigned agent")
@click.option("--tags", default=None, help="Filter by tags (comma-separated)")
@click.option("--full", is_flag=True, default=False, help="Show full task details instead of compressed summaries")
def board_search(
    query: str,
    priority: str | None,
    column: str | None,
    scope: str | None,
    agent: str | None,
    tags: str | None,
    full: bool,
) -> None:
    handle_board_search(
        query,
        filters=BoardSearchFilters(
            priority=priority,
            column=column,
            scope=scope,
            agent=agent,
            tags=tags,
        ),
        full=full,
    )
