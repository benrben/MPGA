"""Tests for mpga ctx command group."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner


def _setup_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.ctx.find_project_root", lambda: str(tmp_path))
    (tmp_path / ".mpga").mkdir(parents=True, exist_ok=True)


def test_ctx_index_search_and_stats(tmp_path: Path, monkeypatch) -> None:
    _setup_project(tmp_path, monkeypatch)
    from mpga.commands.ctx import ctx

    runner = CliRunner()
    index = runner.invoke(ctx, ["index", "--source", "test", "--content", "alpha beta gamma"])
    assert index.exit_code == 0
    assert "artifact_id=" in index.output

    search = runner.invoke(ctx, ["search", "alpha"])
    assert search.exit_code == 0
    assert "test" in search.output

    stats = runner.invoke(ctx, ["stats"])
    assert stats.exit_code == 0
    assert "ctx_index" in stats.output


def test_ctx_execute_and_batch_execute(tmp_path: Path, monkeypatch) -> None:
    _setup_project(tmp_path, monkeypatch)
    from mpga.commands.ctx import ctx

    runner = CliRunner()
    single = runner.invoke(ctx, ["execute", "--code", "printf 'hello from ctx'"])
    assert single.exit_code == 0
    assert "exit_code=0" in single.output

    batch = runner.invoke(
        ctx,
        [
            "batch-execute",
            "--command",
            "printf 'red fox'",
            "--command",
            "printf 'blue whale'",
            "--query",
            "fox",
        ],
    )
    assert batch.exit_code == 0
    assert "results" in batch.output
    assert "fox" in batch.output


def test_ctx_execute_file_and_doctor(tmp_path: Path, monkeypatch) -> None:
    _setup_project(tmp_path, monkeypatch)
    from mpga.commands.ctx import ctx

    src = tmp_path / "demo.txt"
    src.write_text("line1\nline2 token\nline3 token\n", encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(ctx, ["execute-file", str(src), "--query", "token"])
    assert res.exit_code == 0
    assert "matches=2" in res.output

    doctor = runner.invoke(ctx, ["doctor"])
    assert doctor.exit_code == 0
    assert "policy_mode" in doctor.output
    assert "ctx_artifacts_table" in doctor.output
