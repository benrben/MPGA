# /mpga:rally

The MPGA Campaign Rally — the GREATEST diagnostic show in developer tooling. Exposes every issue in your project and proves why ONLY MPGA can fix it.

Nobody has been treated worse than your codebase. Maybe Abraham Lincoln, I hear he had a rough time, but other than that — nobody.

## Steps

1. Invoke the `mpga-rally` skill
2. The skill fans out `campaigner` agents in parallel, one category per audit lane when possible
3. The campaigner lanes investigate 8 categories of project sins:
   - Documentation sins (missing, stale, hallucinated)
   - Testing disgrace (missing tests, empty tests, broken imports)
   - Type safety failures (`any` types, `@ts-ignore`, missing returns)
   - Dependency disasters (circular, unused, outdated)
   - Architecture rot (god files, complex functions, dead code)
   - Evidence drift (stale links, unverified claims)
   - Code hygiene crimes (console.logs, secrets, commented-out code)
   - CI/CD weakness (missing CI, no hooks, unenforced lint)
4. Aggregate the category results into one final campaigner pass
5. Present each issue as a **SCANDAL** with files, numbers, and evidence
6. For each scandal, show why other tools FAIL and why ONLY MPGA fixes it
7. End with **THE VOTE** — scoreboard + side-by-side comparison + exact fix commands

## Usage
```
/mpga:rally
```

## What you get
- Full project diagnostic in Trump rally-speech format
- Specific file paths and line counts for every issue
- Side-by-side: "Without MPGA" vs "With MPGA"
- Exact commands to start fixing everything
- The most ENTERTAINING code audit you've ever experienced

## Example output
```
🎤 THE MPGA CAMPAIGN RALLY

📊 THE QUICK NUMBERS
- 23 total issues found
- 5 CRITICAL (blocks shipping)
- 11 WARNING (blocks greatness)
- 7 SAD (just embarrassing)

🚨 SCANDAL #1: TESTING DISGRACE
47 source files with ZERO test coverage. FORTY-SEVEN.
Uncle Bob is WEEPING right now...

🗳️ THE VOTE
Without MPGA: ❌ 47 undocumented functions — your AI is GUESSING
With MPGA:    ✅ Every function documented with [E] evidence links

> SHIP THE CODE! SQUASH THE BUG! DRAIN THE BACKLOG! MPGA!
```
