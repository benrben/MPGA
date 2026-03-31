"""
Tests that CI workflow files are correctly configured for Python/pytest.

RED phase: these tests FAIL against the Node.js-era workflow files.
GREEN phase: they PASS after the workflows are rewritten for Python.
"""

import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]  # /Users/benreich/MPGA
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
MPGA_YML = REPO_ROOT / ".github" / "workflows" / "mpga.yml"


def _all_run_steps(workflow: dict) -> list[str]:
    """Return all 'run' values from every job step in the workflow."""
    commands: list[str] = []
    jobs = workflow.get("jobs", {})
    for job in jobs.values():
        for step in job.get("steps", []):
            if "run" in step:
                commands.append(step["run"])
    return commands


def _all_step_names(workflow: dict) -> list[str]:
    """Return all step 'name' values from every job in the workflow."""
    names: list[str] = []
    jobs = workflow.get("jobs", {})
    for job in jobs.values():
        for step in job.get("steps", []):
            if "name" in step:
                names.append(step["name"])
    return names


class TestCiYml:
    """ci.yml must be a Python/pytest workflow, not a Node.js workflow."""

    def setup_method(self):
        self.workflow = yaml.safe_load(CI_YML.read_text())
        self.run_commands = _all_run_steps(self.workflow)
        self.combined = "\n".join(self.run_commands)

    def test_does_not_use_npm_ci(self):
        """npm ci must NOT appear — this is a Python project."""
        assert "npm ci" not in self.combined, (
            "ci.yml still calls 'npm ci' — this is a Python project, not Node"
        )

    def test_does_not_use_npm_test(self):
        """npm test must NOT appear — tests run via pytest."""
        assert "npm test" not in self.combined, (
            "ci.yml still calls 'npm test' — Python tests use pytest"
        )

    def test_uses_pytest(self):
        """pytest or python -m pytest must appear somewhere in the run steps."""
        has_pytest = any(
            "pytest" in cmd or "python -m pytest" in cmd
            for cmd in self.run_commands
        )
        assert has_pytest, (
            "ci.yml has no pytest invocation — 786 tests are never run on CI"
        )

    def test_uses_pip_install(self):
        """pip install must appear — Python package installation."""
        has_pip = any("pip install" in cmd for cmd in self.run_commands)
        assert has_pip, (
            "ci.yml has no 'pip install' step — Python deps are never installed"
        )

    def test_does_not_use_npm_install(self):
        """npm install must NOT appear as the main install step."""
        assert "npm install -g" not in self.combined, (
            "ci.yml still calls 'npm install -g' — Python project uses pip"
        )

    def test_targets_python_versions(self):
        """Matrix must specify python-version, not node-version."""
        matrix = (
            self.workflow.get("jobs", {})
            .get(next(iter(self.workflow.get("jobs", {}))), {})
            .get("strategy", {})
            .get("matrix", {})
        )
        assert "python-version" in matrix, (
            f"ci.yml matrix has no python-version key — found: {list(matrix.keys())}"
        )
        assert "node-version" not in matrix, (
            "ci.yml matrix still has node-version — should be python-version"
        )


class TestMpgaYml:
    """mpga.yml must install the CLI via pip, not npm."""

    def setup_method(self):
        self.workflow = yaml.safe_load(MPGA_YML.read_text())
        self.run_commands = _all_run_steps(self.workflow)
        self.combined = "\n".join(self.run_commands)

    def test_does_not_use_npm_install_g(self):
        """npm install -g mpga must NOT appear."""
        assert "npm install -g mpga" not in self.combined, (
            "mpga.yml still uses 'npm install -g mpga' — should use pip install"
        )

    def test_uses_pip_install(self):
        """pip install must appear for installing the mpga CLI."""
        has_pip = any("pip install" in cmd for cmd in self.run_commands)
        assert has_pip, (
            "mpga.yml has no 'pip install' step — CLI never installed on CI"
        )

    def test_does_not_use_setup_node(self):
        """actions/setup-node must NOT be used — this is Python."""
        uses_values = []
        jobs = self.workflow.get("jobs", {})
        for job in jobs.values():
            for step in job.get("steps", []):
                if "uses" in step:
                    uses_values.append(step["uses"])
        node_steps = [u for u in uses_values if "setup-node" in u]
        assert not node_steps, (
            f"mpga.yml still uses setup-node: {node_steps} — Python project uses setup-python"
        )
