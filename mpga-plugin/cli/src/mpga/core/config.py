from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeLayerConfig:
    conventions: list[str] = field(default_factory=list)
    key_file_roles: dict[str, str] = field(default_factory=dict)


@dataclass
class ProjectConfig:
    name: str = ""
    languages: list[str] = field(default_factory=lambda: ["typescript"])
    entry_points: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=lambda: ["node_modules", "dist", ".git", "MPGA/"])


@dataclass
class EvidenceConfig:
    strategy: str = "hybrid"  # hybrid | ast-only | line-only
    line_ranges: bool = True
    ast_anchors: bool = True
    auto_heal: bool = True
    coverage_threshold: float = 0.2


@dataclass
class DriftConfig:
    ci_threshold: int = 80
    hook_mode: str = "quick"  # quick | report
    auto_sync: bool = False


@dataclass
class TiersConfig:
    hot_max_lines: int = 500
    warm_max_lines_per_scope: int = 300
    cold_auto_archive_after_days: int = 30


@dataclass
class MilestoneConfig:
    branch_strategy: str = "worktree"  # worktree | branch
    auto_advance: bool = False
    squash_on_complete: bool = True


@dataclass
class AgentsConfig:
    tdd_cycle: bool = True
    exploration_cycle: bool = True
    research_before_plan: bool = True


@dataclass
class ScopesConfig:
    scope_depth: int | str = "auto"  # int or 'auto'
    max_files_per_scope: int = 15


@dataclass
class BoardConfig:
    columns: list[str] = field(
        default_factory=lambda: ["backlog", "todo", "in-progress", "testing", "review", "done"]
    )
    custom_columns: list[str] = field(default_factory=list)
    wip_limits: dict[str, int] = field(
        default_factory=lambda: {"in-progress": 3, "testing": 3, "review": 2}
    )
    auto_transitions: bool = True
    archive_on_milestone_complete: bool = True
    task_id_prefix: str = "T"
    default_priority: str = "medium"
    default_time_estimate: str = "5min"
    show_tdd_stage: bool = True
    show_evidence_status: bool = True
    github_sync: bool = False


@dataclass
class MpgaConfig:
    version: str = "1.0.0"
    project: ProjectConfig = field(default_factory=ProjectConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    drift: DriftConfig = field(default_factory=DriftConfig)
    tiers: TiersConfig = field(default_factory=TiersConfig)
    milestone: MilestoneConfig = field(default_factory=MilestoneConfig)
    agents: AgentsConfig = field(default_factory=AgentsConfig)
    scopes: ScopesConfig = field(default_factory=ScopesConfig)
    board: BoardConfig = field(default_factory=BoardConfig)
    knowledge_layer: KnowledgeLayerConfig | None = None


def default_config() -> MpgaConfig:
    cfg = MpgaConfig()
    cfg.project.name = Path.cwd().name
    return cfg


# Convenience alias for tests and code that expects a constant-like name
DEFAULT_CONFIG = default_config()


# -- JSON key mapping (camelCase <-> snake_case) --------------------------------

_CAMEL_TO_SNAKE = {
    "entryPoints": "entry_points",
    "lineRanges": "line_ranges",
    "astAnchors": "ast_anchors",
    "autoHeal": "auto_heal",
    "coverageThreshold": "coverage_threshold",
    "ciThreshold": "ci_threshold",
    "hookMode": "hook_mode",
    "autoSync": "auto_sync",
    "hotMaxLines": "hot_max_lines",
    "warmMaxLinesPerScope": "warm_max_lines_per_scope",
    "coldAutoArchiveAfterDays": "cold_auto_archive_after_days",
    "branchStrategy": "branch_strategy",
    "autoAdvance": "auto_advance",
    "squashOnComplete": "squash_on_complete",
    "tddCycle": "tdd_cycle",
    "explorationCycle": "exploration_cycle",
    "researchBeforePlan": "research_before_plan",
    "scopeDepth": "scope_depth",
    "maxFilesPerScope": "max_files_per_scope",
    "customColumns": "custom_columns",
    "wipLimits": "wip_limits",
    "autoTransitions": "auto_transitions",
    "archiveOnMilestoneComplete": "archive_on_milestone_complete",
    "taskIdPrefix": "task_id_prefix",
    "defaultPriority": "default_priority",
    "defaultTimeEstimate": "default_time_estimate",
    "showTddStage": "show_tdd_stage",
    "showEvidenceStatus": "show_evidence_status",
    "githubSync": "github_sync",
    "knowledgeLayer": "knowledge_layer",
    "keyFileRoles": "key_file_roles",
}

_SNAKE_TO_CAMEL = {v: k for k, v in _CAMEL_TO_SNAKE.items()}

_SECTION_MAP = {
    "project": ProjectConfig,
    "evidence": EvidenceConfig,
    "drift": DriftConfig,
    "tiers": TiersConfig,
    "milestone": MilestoneConfig,
    "agents": AgentsConfig,
    "scopes": ScopesConfig,
    "board": BoardConfig,
    "knowledge_layer": KnowledgeLayerConfig,
}


def _convert_keys(d: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in d.items():
        new_key = mapping.get(k, k)
        if isinstance(v, dict):
            result[new_key] = _convert_keys(v, mapping)
        else:
            result[new_key] = v
    return result


def _dict_to_config(raw: dict[str, Any]) -> MpgaConfig:
    """Convert a JSON dict (camelCase keys) into an MpgaConfig."""
    data = _convert_keys(raw, _CAMEL_TO_SNAKE)
    cfg = default_config()
    if "version" in data:
        cfg.version = data["version"]
    for section_name, cls in _SECTION_MAP.items():
        if section_name in data and isinstance(data[section_name], dict):
            section_data = data[section_name]
            section_obj = getattr(cfg, section_name) or cls()
            for k, v in section_data.items():
                if hasattr(section_obj, k):
                    setattr(section_obj, k, v)
            setattr(cfg, section_name, section_obj)
    return cfg


def _config_to_dict(cfg: MpgaConfig) -> dict[str, Any]:
    """Convert an MpgaConfig to a JSON-serializable dict with camelCase keys."""
    from dataclasses import asdict

    raw = asdict(cfg)
    if raw.get("knowledge_layer") is None:
        del raw["knowledge_layer"]
    return _convert_keys(raw, _SNAKE_TO_CAMEL)


# -- Filesystem operations -------------------------------------------------------


def find_project_root(start_dir: str | Path | None = None) -> Path | None:
    d = Path(start_dir) if start_dir else Path.cwd()
    while True:
        if (d / "mpga.config.json").exists():
            return d
        if (d / "MPGA" / "mpga.config.json").exists():
            return d
        parent = d.parent
        if parent == d:
            return None
        d = parent


def load_config(project_root: str | Path | None = None) -> MpgaConfig:
    root = Path(project_root) if project_root else (find_project_root() or Path.cwd())
    config_path = root / "mpga.config.json"
    if not config_path.exists():
        config_path = root / "MPGA" / "mpga.config.json"

    if not config_path.exists():
        cfg = default_config()
        cfg.project.name = root.name
        return cfg

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    cfg = _dict_to_config(raw)
    return cfg


def save_config(config: MpgaConfig, config_path: str | Path) -> None:
    p = Path(config_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_config_to_dict(config), indent=2) + "\n", encoding="utf-8")


def get_config_value(config: MpgaConfig, key: str) -> Any:
    parts = key.split(".")
    obj: Any = config
    for part in parts:
        snake = _CAMEL_TO_SNAKE.get(part, part)
        if hasattr(obj, snake):
            obj = getattr(obj, snake)
        elif hasattr(obj, part):
            obj = getattr(obj, part)
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def set_config_value(config: MpgaConfig, key: str, value: str) -> None:
    parts = key.split(".")
    obj: Any = config
    for part in parts[:-1]:
        snake = _CAMEL_TO_SNAKE.get(part, part)
        if hasattr(obj, snake):
            obj = getattr(obj, snake)
        elif hasattr(obj, part):
            obj = getattr(obj, part)
    last = parts[-1]
    snake_last = _CAMEL_TO_SNAKE.get(last, last)
    attr = snake_last if hasattr(obj, snake_last) else last
    existing = getattr(obj, attr, None)
    if isinstance(existing, bool):  # bool before int — bool is subclass of int in Python
        setattr(obj, attr, value.lower() == "true")
    elif isinstance(existing, int):
        setattr(obj, attr, int(value))
    elif isinstance(existing, float):
        setattr(obj, attr, float(value))
    else:
        setattr(obj, attr, value)
