"""
Tests for agent prompt and token optimization tasks T047-T055.

Coverage checklist:
  T047: red-dev.md — single-char string edge case in TPP ladder
  T048: blue-dev.md — docstring scope constraint
  T049: optimizer.md — brittle path arithmetic as high-priority smell
  T050: simplify SKILL.md — skipped targets summary at end of run
  T051: ship SKILL.md — gate checks use mpga CLI commands
  T052: blue-dev.md — line count reduced (token optimization)
  T053: security-auditor.md — char count reduced (token optimization)
  T054: red-dev.md — TPP list replaced with reference link (token optimization)
  T055: rally SKILL.md — char count reduced (token optimization)
"""

import pathlib

AGENTS_DIR = pathlib.Path(__file__).parent.parent.parent / "agents"
SKILLS_DIR = pathlib.Path(__file__).parent.parent.parent / "skills"

# Baselines captured before GREEN phase
BLUE_DEV_BASELINE_LINES = 131   # wc -l before optimization
SECURITY_AUDITOR_BASELINE_CHARS = 12206
RED_DEV_BASELINE_CHARS = 11549
RALLY_BASELINE_CHARS = 4375


# ---------------------------------------------------------------------------
# T047: red-dev.md — single-char string edge case in TPP ladder
# ---------------------------------------------------------------------------

def test_t047_red_dev_single_char_edge_case():
    """RED: red-dev.md must mention single-char or single-character string edge case in TPP ladder."""
    content = (AGENTS_DIR / "red-dev.md").read_text()
    mentions_single_char = (
        "single-char" in content.lower()
        or "single-character" in content.lower()
        or "single character" in content.lower()
    )
    assert mentions_single_char, (
        "red-dev.md must mention single-char string edge cases in the TPP ladder section. "
        "Add: testing single-character strings, empty strings, and boundary cases as required edge cases."
    )


# ---------------------------------------------------------------------------
# T048: blue-dev.md — docstring scope constraint
# ---------------------------------------------------------------------------

def test_t048_blue_dev_docstring_scope_constraint():
    """RED: blue-dev.md must contain a rule about only adding docstrings when explicitly requested."""
    content = (AGENTS_DIR / "blue-dev.md").read_text()
    has_constraint = (
        "docstring" in content.lower()
        and (
            "explicitly" in content.lower()
            or "only if" in content.lower()
            or "only when" in content.lower()
        )
    )
    assert has_constraint, (
        "blue-dev.md must contain a rule like: "
        "'Only add docstrings, type annotations, or comments if the task explicitly requests them.' "
        "The blue phase is for structural cleanup, not documentation generation."
    )


# ---------------------------------------------------------------------------
# T049: optimizer.md — brittle path arithmetic as high-priority smell
# ---------------------------------------------------------------------------

def test_t049_optimizer_path_arithmetic_smell():
    """RED: optimizer.md must mention path arithmetic or pathlib as a code smell."""
    content = (AGENTS_DIR / "optimizer.md").read_text()
    has_smell = (
        "path arithmetic" in content.lower()
        or "pathlib" in content.lower()
    )
    assert has_smell, (
        "optimizer.md must mention 'Brittle path arithmetic (string slicing/indexing instead of pathlib.Path)' "
        "as a HIGH priority smell in the smell catalog."
    )


# ---------------------------------------------------------------------------
# T050: simplify SKILL.md — skipped targets summary at end of run
# ---------------------------------------------------------------------------

def test_t050_simplify_skipped_targets_summary():
    """RED: simplify SKILL.md must mention printing a summary of skipped targets with reasons."""
    skill_file = SKILLS_DIR / "simplify" / "SKILL.md"
    content = skill_file.read_text()
    has_skipped_summary = (
        "skipped" in content.lower()
        and "summary" in content.lower()
        and "reason" in content.lower()
    )
    assert has_skipped_summary, (
        "simplify SKILL.md must state: 'At the end of the run, print a summary of any targets "
        "that were skipped and the reason.' Add this to the output spec."
    )


# ---------------------------------------------------------------------------
# T051: ship SKILL.md — gate checks use mpga CLI
# ---------------------------------------------------------------------------

def test_t051_ship_gate_checks_use_mpga_cli():
    """RED: ship SKILL.md gate checks must reference mpga CLI commands (mpga health, mpga drift, mpga evidence verify)."""
    skill_file = SKILLS_DIR / "ship" / "SKILL.md"
    content = skill_file.read_text()
    # The file should reference mpga health as a gate check (not just raw bash equivalents)
    has_mpga_health = "mpga health" in content
    assert has_mpga_health, (
        "ship SKILL.md gate checks must use mpga CLI commands. "
        "Add 'mpga health' as an explicit gate check in Phase 1."
    )


# ---------------------------------------------------------------------------
# T052: blue-dev.md — line count reduced (token optimization)
# ---------------------------------------------------------------------------

def test_t052_blue_dev_line_count_reduced():
    """RED/GREEN check: blue-dev.md must have fewer than baseline - 20 lines after optimization."""
    content = (AGENTS_DIR / "blue-dev.md").read_text()
    line_count = len(content.splitlines())
    target = BLUE_DEV_BASELINE_LINES - 20  # 111
    assert line_count < target, (
        f"blue-dev.md has {line_count} lines; expected < {target} (baseline {BLUE_DEV_BASELINE_LINES} - 20). "
        "Convert Kent Beck prose paragraphs to concise bullet points to reduce token overhead."
    )


# ---------------------------------------------------------------------------
# T053: security-auditor.md — char count reduced (token optimization)
# ---------------------------------------------------------------------------

def test_t053_security_auditor_char_count_reduced():
    """RED/GREEN check: security-auditor.md must have fewer than baseline - 400 chars after optimization."""
    content = (AGENTS_DIR / "security-auditor.md").read_text()
    char_count = len(content)
    target = SECURITY_AUDITOR_BASELINE_CHARS - 400  # 11806
    assert char_count < target, (
        f"security-auditor.md has {char_count} chars; expected < {target} "
        f"(baseline {SECURITY_AUDITOR_BASELINE_CHARS} - 400). "
        "Condense OWASP checklist prose paragraphs to tight bullets."
    )


# ---------------------------------------------------------------------------
# T054: red-dev.md — TPP list replaced with reference link (token optimization)
# ---------------------------------------------------------------------------

def test_t054_red_dev_tpp_reference_link():
    """RED/GREEN check: red-dev.md char count must be reduced by at least 200 chars after TPP list → reference."""
    content = (AGENTS_DIR / "red-dev.md").read_text()
    char_count = len(content)
    target = RED_DEV_BASELINE_CHARS - 200  # 11349
    assert char_count < target, (
        f"red-dev.md has {char_count} chars; expected < {target} "
        f"(baseline {RED_DEV_BASELINE_CHARS} - 200). "
        "Replace the verbose inline TPP list with a reference link to save tokens."
    )


# ---------------------------------------------------------------------------
# T055: rally SKILL.md — char count reduced (token optimization)
# ---------------------------------------------------------------------------

def test_t055_rally_char_count_reduced():
    """RED/GREEN check: rally SKILL.md must have fewer than baseline - 300 chars after prose trimming."""
    skill_file = SKILLS_DIR / "rally" / "SKILL.md"
    content = skill_file.read_text()
    char_count = len(content)
    target = RALLY_BASELINE_CHARS - 300  # 4075
    assert char_count < target, (
        f"rally SKILL.md has {char_count} chars; expected < {target} "
        f"(baseline {RALLY_BASELINE_CHARS} - 300). "
        "Trim redundant marketing prose while keeping actual instructions."
    )


# ---------------------------------------------------------------------------
# T063: rally SKILL.md — parallelism instruction for Agent tool
# ---------------------------------------------------------------------------

def test_t063_rally_parallel_agent_invocation():
    """RED: rally SKILL.md must explicitly instruct using multiple Agent tool calls in a single message."""
    skill_file = SKILLS_DIR / "rally" / "SKILL.md"
    content = skill_file.read_text()
    lower = content.lower()
    has_parallel_agent_instruction = (
        "agent tool" in lower
        or "agent calls" in lower
        or "multiple agent" in lower
    ) and (
        "single message" in lower
        or "same message" in lower
        or "one message" in lower
    )
    assert has_parallel_agent_instruction, (
        "rally SKILL.md Step 2 must explicitly instruct the orchestrator to use "
        "multiple Agent tool calls in a single message for parallel campaigner execution. "
        "The current 'in PARALLEL' wording is ambiguous — add: "
        "'Use multiple Agent tool calls in a single message to run them concurrently.'"
    )


# ---------------------------------------------------------------------------
# T008: cli-runner agent definition
# ---------------------------------------------------------------------------

def test_t008_cli_runner_agent_exists():  # T008
    """RED: cli-runner.md must exist with correct name, allowlist safety, and mpga command references."""
    agent_file = AGENTS_DIR / "cli-runner.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/cli-runner.md does not exist. "
        "Create the cli-runner agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as cli-runner in frontmatter
    assert "cli-runner" in content, (
        "cli-runner.md must contain 'cli-runner' (e.g. in the name: frontmatter field)."
    )

    # Must mention allowlist (safety requirement)
    has_allowlist = "allowlist" in content.lower() or "allow list" in content.lower()
    assert has_allowlist, (
        "cli-runner.md must mention 'allowlist' or 'allow list' as a safety mechanism "
        "to restrict which commands can be executed."
    )

    # Must mention mpga commands
    assert "mpga" in content, (
        "cli-runner.md must mention 'mpga' commands as the commands this agent executes."
    )


# ---------------------------------------------------------------------------
# T009: searcher agent definition
# ---------------------------------------------------------------------------

def test_t009_searcher_agent_exists():  # T009
    """RED: searcher.md must exist with correct name, search commands, and evidence link references."""
    searcher_file = AGENTS_DIR / "searcher.md"
    assert searcher_file.exists(), (
        "mpga-plugin/agents/searcher.md does not exist. "
        "Create the searcher agent definition file."
    )
    content = searcher_file.read_text()
    lower = content.lower()

    # Check name frontmatter contains "searcher"
    assert "name: searcher" in lower, (
        "searcher.md frontmatter must contain 'name: searcher'."
    )

    # Check it mentions mpga search or mpga board search
    has_search_cmd = "mpga search" in content or "mpga board search" in content
    assert has_search_cmd, (
        "searcher.md must mention 'mpga search' or 'mpga board search' commands."
    )

    # Check it mentions evidence links or [E]
    has_evidence = "[E]" in content or "evidence link" in lower
    assert has_evidence, (
        "searcher.md must mention evidence links or '[E]' citations in its output spec."
    )


# ---------------------------------------------------------------------------
# T010: context-builder agent definition
# ---------------------------------------------------------------------------

def test_t010_context_builder_agent_exists():  # T010
    """RED: context-builder.md must exist with correct name, task card reference, and mpga command usage."""
    agent_file = AGENTS_DIR / "context-builder.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/context-builder.md does not exist. "
        "Create the context-builder agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as context-builder
    assert "context-builder" in content, (
        "context-builder.md must contain 'context-builder' (e.g. in the name: frontmatter field)."
    )

    # Must mention acceptance criteria or task card
    has_task_ref = (
        "acceptance criteria" in content.lower()
        or "task card" in content.lower()
    )
    assert has_task_ref, (
        "context-builder.md must mention 'acceptance criteria' or 'task card' — "
        "this agent assembles context packages including the task's acceptance criteria."
    )

    # Must reference mpga board or mpga scope commands
    has_mpga_cmd = (
        "mpga board" in content
        or "mpga scope" in content
    )
    assert has_mpga_cmd, (
        "context-builder.md must reference 'mpga board' or 'mpga scope' CLI commands — "
        "these are the primary tools for loading task and scope context."
    )


# ---------------------------------------------------------------------------
# T011: explainer agent definition
# ---------------------------------------------------------------------------

def test_t011_explainer_agent_exists():  # T011
    """RED: explainer.md must exist with read-only constraint and evidence link references."""
    agent_file = AGENTS_DIR / "explainer.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/explainer.md does not exist. "
        "Create the explainer agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as explainer
    assert "explainer" in content.lower(), (
        "explainer.md must contain 'explainer' (e.g. in the name: frontmatter field)."
    )

    # Must mention read-only constraint
    has_readonly = (
        "read-only" in content.lower()
        or "never modif" in content.lower()
    )
    assert has_readonly, (
        "explainer.md must mention 'read-only' or 'never modif' as a constraint — "
        "the explainer agent must never modify files."
    )

    # Must mention evidence links
    has_evidence = (
        "[E]" in content
        or "evidence" in content.lower()
    )
    assert has_evidence, (
        "explainer.md must mention evidence links '[E]' or 'evidence' — "
        "the explainer agent must cite evidence in its output."
    )


# ---------------------------------------------------------------------------
# T013: doc-writer agent definition
# ---------------------------------------------------------------------------

def test_t013_doc_writer_agent_exists():  # T013
    """RED: doc-writer.md must exist with correct name, evidence citations, and a never-guess rule."""
    agent_file = AGENTS_DIR / "doc-writer.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/doc-writer.md does not exist. "
        "Create the doc-writer agent definition file."
    )
    content = agent_file.read_text()
    lower = content.lower()

    # Must declare name as doc-writer
    assert "doc-writer" in content, (
        "doc-writer.md must contain 'doc-writer' (e.g. in the name: frontmatter field)."
    )

    # Must mention evidence (doc-writer cites evidence for every claim)
    assert "evidence" in lower, (
        "doc-writer.md must mention 'evidence' — the agent must cite evidence for every factual claim."
    )

    # Must include a never-guess / never-document-what-doesn't-exist rule
    has_never_rule = "never" in lower and (
        "guess" in lower
        or "document" in lower
        or "implement" in lower
    )
    assert has_never_rule, (
        "doc-writer.md must contain a rule using 'never' combined with 'guess', 'document', or 'implement' "
        "— the agent must not document features that aren't implemented."
    )


# ---------------------------------------------------------------------------
# T016: test-generator agent definition
# ---------------------------------------------------------------------------

def test_t016_test_generator_agent_exists():  # T016
    """RED: test-generator.md must exist with correct name, behavior-testing constraint, and edge case coverage."""
    agent_file = AGENTS_DIR / "test-generator.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/test-generator.md does not exist. "
        "Create the test-generator agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as test-generator
    assert "test-generator" in content, (
        "test-generator.md must contain 'test-generator' (e.g. in the name: frontmatter field)."
    )

    # Must mention testing behavior, not internals
    has_behavior = (
        "behavior" in content.lower()
        or "behaviour" in content.lower()
    )
    assert has_behavior, (
        "test-generator.md must mention 'behavior' or 'behaviour' — "
        "tests must verify observable behavior, not implementation internals."
    )

    # Must mention edge cases or boundary values
    has_edge_or_boundary = (
        "edge case" in content.lower()
        or "boundary" in content.lower()
    )
    assert has_edge_or_boundary, (
        "test-generator.md must mention 'edge case' or 'boundary' — "
        "the agent must generate tests covering edge cases and boundary values."
    )


# ---------------------------------------------------------------------------
# T015: migrator agent definition
# ---------------------------------------------------------------------------

def test_t015_migrator_agent_exists():  # T015
    """RED: migrator.md must exist with correct name, idempotency, and rollback references."""
    agent_file = AGENTS_DIR / "migrator.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/migrator.md does not exist. "
        "Create the migrator agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as migrator
    assert "migrator" in content.lower(), (
        "migrator.md must contain 'migrator' (e.g. in the name: frontmatter field)."
    )

    # Must mention idempotency
    assert "idempoten" in content.lower(), (
        "migrator.md must mention 'idempotent' or 'idempotency' — "
        "migrations must be safe to run multiple times (IF NOT EXISTS, etc.)."
    )

    # Must mention rollback or down migration
    has_rollback = (
        "rollback" in content.lower()
        or "down migration" in content.lower()
    )
    assert has_rollback, (
        "migrator.md must mention 'rollback' or 'down migration' — "
        "every migration must include a way to reverse the schema change."
    )


# ---------------------------------------------------------------------------
# T017: profiler agent definition
# ---------------------------------------------------------------------------

def test_t017_profiler_agent_exists():  # T017
    """RED: profiler.md must exist and describe Python/SQLite performance profiling."""
    agent_file = AGENTS_DIR / "profiler.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/profiler.md does not exist. "
        "Create the profiler agent definition file."
    )
    content = agent_file.read_text()
    lower = content.lower()

    # Must contain "profiler" in the content
    assert "profiler" in lower, (
        "profiler.md must contain 'profiler' (e.g. in the name: frontmatter field)."
    )

    # Must mention Python profiling tools (cProfile or line_profiler)
    has_python_profiler = (
        "cprofile" in lower
        or "cProfile" in content
        or "line_profiler" in lower
    )
    assert has_python_profiler, (
        "profiler.md must mention 'cProfile' or 'line_profiler' as Python profiling tools."
    )

    # Must mention SQLite query plan analysis
    has_sqlite_profiler = (
        "explain" in lower
        or "query plan" in lower
    )
    assert has_sqlite_profiler, (
        "profiler.md must mention 'EXPLAIN' or 'query plan' for SQLite profiling."
    )


# ---------------------------------------------------------------------------
# T014: hook-manager agent definition
# ---------------------------------------------------------------------------

def test_t014_hook_manager_agent_exists():  # T014
    """RED: hook-manager.md must exist with hook types, safety validation, and injection checks."""
    agent_file = AGENTS_DIR / "hook-manager.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/hook-manager.md does not exist. "
        "Create the hook-manager agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as hook-manager
    assert "hook-manager" in content, (
        "hook-manager.md must contain 'hook-manager' (e.g. in the name: frontmatter field)."
    )

    # Must mention allowed hook types
    has_hook_types = "PreToolUse" in content or "PostToolUse" in content
    assert has_hook_types, (
        "hook-manager.md must mention 'PreToolUse' or 'PostToolUse' as allowed hook types."
    )

    # Must mention safety — injection or validation
    has_safety = "injection" in content.lower() or "validat" in content.lower()
    assert has_safety, (
        "hook-manager.md must mention 'injection' or 'validat' as a safety requirement."
    )


# ---------------------------------------------------------------------------
# T012: dependency-analyst agent definition
# ---------------------------------------------------------------------------

def test_t012_dependency_analyst_agent_exists():  # T012
    """RED: dependency-analyst.md must exist with correct name, vulnerability checks, and manifest references."""
    agent_file = AGENTS_DIR / "dependency-analyst.md"
    assert agent_file.exists(), (
        "mpga-plugin/agents/dependency-analyst.md does not exist. "
        "Create the dependency-analyst agent definition file."
    )
    content = agent_file.read_text()

    # Must declare name as dependency-analyst in frontmatter
    assert "dependency-analyst" in content, (
        "dependency-analyst.md must contain 'dependency-analyst' (e.g. in the name: frontmatter field)."
    )

    # Must mention vulnerability/vulnerable
    assert "vulnerabilit" in content.lower(), (
        "dependency-analyst.md must mention 'vulnerability' or 'vulnerable' — "
        "this agent exists to catch security vulnerabilities in dependencies."
    )

    # Must mention at least one supported manifest file
    has_manifest = (
        "pyproject" in content.lower()
        or "package.json" in content.lower()
        or "uv.lock" in content.lower()
    )
    assert has_manifest, (
        "dependency-analyst.md must mention at least one dependency manifest file: "
        "pyproject.toml, package.json, or uv.lock."
    )
