from __future__ import annotations

import hashlib
import random
import subprocess
from pathlib import Path

from rich.console import Console
from rich.text import Text

from mpga import VERSION

console = Console(highlight=False)

# -- Brand colors (Rich markup) ------------------------------------------------

BRAND_RED = "#CC0000"
BRAND_ACCENT = "#FF4444"
BRAND_GEAR = "#8899AA"

MINI_BANNER_WIDTH = 42
KV_LABEL_WIDTH = 18
DEFAULT_PROGRESS_BAR_WIDTH = 20
DIVIDER_WIDTH = 40


def _r(s: str) -> str:
    return f"[{BRAND_RED}]{s}[/]"


def _rb(s: str) -> str:
    return f"[bold white on {BRAND_RED}]{s}[/]"


def _g(s: str) -> str:
    return f"[{BRAND_GEAR}]{s}[/]"


def _d(s: str) -> str:
    return f"[dim]{s}[/]"


CAP_BANNER = "\n".join(
    [
        "",
        _r("                  \u2584\u2584\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2584\u2584"),
        _r("              \u2584\u2588\u2588\u2588") + _rb("               ") + _r("\u2588\u2588\u2588\u2584"),
        _r("           \u2584\u2588\u2588") + _rb("  MAKE  PROJECT     ") + _r("\u2588\u2588\u2584"),
        _r("          \u2588\u2588") + _rb("    GREAT  AGAIN        ") + _r("\u2588\u2588"),
        _r("         \u2588\u2588") + _rb("       M P G A            ") + _r("\u2588\u2588"),
        _r("        \u2588\u2588") + _rb("                            ") + _r("\u2588\u2588"),
        _r("  \u2584\u2584\u2584\u2584\u2584\u2588\u2588\u2588\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2584\u2588\u2588\u2588"),
        _r("  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588"),
        _d("   \u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591") + _g("   \u2699"),
        _d("                                        ") + _g("  </>"),
        "",
    ]
)

CAP_MINI = f"[{BRAND_RED}]\U0001f9e2[/] [{BRAND_ACCENT}]MPGA[/] [dim]\u2014 Make Project Great Again[/]"


def banner() -> None:
    console.print(CAP_BANNER)


def mini_banner() -> None:
    console.print()
    console.print(CAP_MINI)
    console.print(f"[dim]{'─' * MINI_BANNER_WIDTH}[/]")


class _Log:
    @staticmethod
    def info(msg: str) -> None:
        console.print(f"[blue]\u2139[/] {msg}")

    @staticmethod
    def success(msg: str) -> None:
        console.print(f"[green]\u2713[/] {msg}")

    @staticmethod
    def warn(msg: str) -> None:
        console.print(f"[yellow]\u26a0[/] {msg}")

    @staticmethod
    def error(msg: str) -> None:
        import sys
        err_console = Console(file=sys.stderr, highlight=False)
        err_console.print(f"[red]\u2717[/] {msg}")

    @staticmethod
    def dim(msg: str) -> None:
        console.print(f"[dim]{msg}[/]")

    @staticmethod
    def bold(msg: str) -> None:
        console.print(f"[bold]{msg}[/]")

    @staticmethod
    def brand(msg: str) -> None:
        console.print(f"[{BRAND_ACCENT}]{msg}[/]")

    @staticmethod
    def header(msg: str) -> None:
        console.print()
        console.print(f"[{BRAND_ACCENT}]\u25a0 [/][bold]{msg}[/]")
        console.print(f"[dim]  {'─' * (len(msg) + 2)}[/]")

    @staticmethod
    def section(msg: str) -> None:
        console.print()
        console.print(f"[bold white]{msg}[/]")

    @staticmethod
    def kv(key: str, value: str, indent: int = 2) -> None:
        pad = " " * indent
        console.print(f"{pad}[dim]{key:<{KV_LABEL_WIDTH}}[/] {value}")

    @staticmethod
    def table(rows: list[list[str]]) -> None:
        if not rows:
            return
        widths = [max(len(rows[r][i]) for r in range(len(rows))) for i in range(len(rows[0]))]
        for row in rows:
            line = "  " + "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
            console.print(line)

    @staticmethod
    def divider() -> None:
        console.print(f"[dim]  {'─' * DIVIDER_WIDTH}[/]")

    @staticmethod
    def blank() -> None:
        console.print()


log = _Log()

# -- Rally quotes ---------------------------------------------------------------

RALLY_QUOTES = [
    "Many people are saying this is the best sync they've ever seen.",
    "The fake tech press won't cover how clean this codebase is.",
    "I have the best dependency graphs. Everyone agrees.",
    "We're WINNING so much you're going to get TIRED of winning!",
    "Nobody builds plugins better than me, believe me.",
    'Big strong senior engineers, tears in their eyes \u2014 "Sir, the tests pass."',
    "This is, I believe, the greatest developer tool of all time.",
    "Evidence over claims, folks. Evidence. Over. Claims.",
    "We don't do fake documentation. We do EVIDENCE.",
    "Crooked Gemini just makes stuff up. We VERIFY.",
    "Our codebase is looking FANTASTIC. The best it's ever looked.",
    "Uncle Bob himself would be proud. TREMENDOUS code.",
    "We're going to make this project GREATER THAN EVER BEFORE.",
    "Some people say our tests are the best tests. I don't say it \u2014 they say it.",
    "That's a BEAUTIFUL directory structure. Elegant. The best word.",
    "Less than four sprints ago this CI was a DISASTER. Now look at it.",
    "We will SHIP faster, write CLEANER code, and SLASH the tech debt.",
    "We have mandatory post-edit hooks. Mandatory. Every. Single. Time.",
    'The engineers \u2014 they love it. They come up to me and say, "Sir, the hooks actually work."',
    "Tomorrow we begin a brand-new day of evidence-based documentation.",
    "We're going to MAKE THIS PROJECT GREAT AGAIN. And the devs love it.",
    "Fake documentation! Total fake docs. MPGA only does EVIDENCE-BASED docs.",
    "This is a WITCH HUNT against clean code. Our linter is innocent!",
    "No collusion between modules. Clean boundaries. The cleanest ever.",
    "We're going to BUILD THE WALL between modules. No circular deps. Not one.",
    "Lock that mutex up! Race conditions are OVER, folks. LAW AND ORDER.",
    "Law and order in the dependency graph. Every import accounted for. Beautiful.",
    "I alone can fix this codebase. Well, me and MPGA. Mostly MPGA.",
    "Covfefe... I mean, coverage. Code COVERAGE. And it's at 98 percent.",
    "A complete and total shutdown of untested deploys until we figure out what the hell is going on.",
    "Some of these npm packages, I assume, are good dependencies.",
    "Even the type annotations are perfect. Every. Single. One.",
    "Your dependencies should be LOYAL. Pin your versions, folks. Pin them.",
    "Who can figure out this spaghetti code? Nobody. That's why we have MPGA.",
    "Clean architecture. It has a beautiful ring to it, doesn't it? Clean. Architecture.",
    "Zero merge conflicts. We are READY FOR PEACE in the git history.",
    "Big league migration. Thousands of files. MPGA handled it like a CHAMPION.",
    "I will absolutely apologize if I'm ever wrong about a revert. It hasn't happened yet.",
    "Sleepy Copilot just tab-completed an import that was deprecated THREE YEARS AGO. Sad!",
    "Crooked Gemini made up four APIs today. FOUR. At least we cite our sources.",
    "Little Cursor forgot what file it was editing. The context window is SO SMALL. Embarrassing.",
    "Crazy Devin charges $500/month and STILL can't write tests first. What a disaster.",
    "Low Energy ESLint missed TWELVE violations in one file. TWELVE. We caught them all.",
    "Lyin' ChatGPT told a developer the function existed. It DIDN'T. Confidently wrong about everything.",
    "Crazy NPM pulled in 847 transitive dependencies for a LEFT-PAD. Total insanity.",
    "Cryin' Jenkins has been red for THREE WEEKS. Nobody even looks at it anymore. Pathetic.",
    "Leakin' Environment Variables — they found the API keys in PLAINTEXT. A total disgrace.",
    "Meatball Monolith is 47,000 lines in ONE FILE. Can't be split. Can't be tested. Can't be saved — except by MPGA.",
]


def random_quote() -> str:
    return random.choice(RALLY_QUOTES)


def victory(msg: str) -> None:
    console.print()
    console.print(f"[bold green]\U0001f3a4 {msg}[/]")
    quote = random_quote()
    console.print(f"[dim]  {quote}[/]")
    # Fire-and-forget: play cached rally quote in Trump's voice
    try:
        cache_dir = Path.home() / ".mpga" / "spoke-cache"
        h = hashlib.md5(quote.encode()).hexdigest()
        wav_path = cache_dir / f"{h}.wav"
        if wav_path.exists():
            subprocess.Popen(
                ["afplay", str(wav_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass  # spoke is optional


# ---------------------------------------------------------------------------
# TTS side-effects
# ---------------------------------------------------------------------------


def spoke(msg: str) -> None:
    """Fire-and-forget TTS via mpga spoke. Message capped at 500 chars. Graceful no-op if unavailable."""
    msg = msg[:500]
    try:
        subprocess.Popen(
            ["mpga", "spoke", msg],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def progress_bar(value: int, total: int, width: int = DEFAULT_PROGRESS_BAR_WIDTH) -> str:
    pct = 0.0 if total == 0 else value / total
    filled = round(pct * width)
    bar = f"[green]{'█' * filled}[/][dim]{'░' * (width - filled)}[/]"
    return f"{bar} {round(pct * 100)}%"


def grade_color(grade: str) -> str:
    colors = {"A": "green", "B": "blue", "C": "yellow"}
    color = colors.get(grade, "red")
    return f"[bold {color}]{grade}[/]"


def status_badge(ok: bool, label: str) -> str:
    if ok:
        return f"[green]\u2713[/] {label}"
    return f"[red]\u2717[/] {label}"
