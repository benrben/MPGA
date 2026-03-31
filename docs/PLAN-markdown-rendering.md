# Plan: Render Markdown in MPGA Console
**Milestone:** M003-render-markdown-in-mpga-console
**Design doc:** [DESIGN-markdown-rendering.md](DESIGN-markdown-rendering.md)
**Target file:** `mpga-plugin/cli/src/mpga/web/static/index.html`

---

## Task Breakdown

### T001: Add marked.js and DOMPurify CDN script tags **[CRITICAL PATH]**
**File:** `index.html:3` (insert after `<head>` opening)
**Scope:** mpga-plugin
**Execution:** serial
**Risk:** Complexity=1 Uncertainty=1 Impact=2 → Score=2 (LOW)
**Critical path:** yes
**Phase:** 1
**Evidence expected:**
- [E] `index.html:3` — `<head>` tag, insertion point for CDN scripts
- [E] `index.html:529` — inline `<script>` block confirms no existing external scripts

**Acceptance criteria:**
- [ ] `<script src="...marked...">` tag present in `<head>` before inline script
- [ ] `<script src="...DOMPurify...">` tag present in `<head>` before inline script
- [ ] `typeof marked !== 'undefined'` evaluates true in browser console after page load
- [ ] `typeof DOMPurify !== 'undefined'` evaluates true in browser console after page load
- [ ] Test: `test_markdown_rendering.py` asserts both script tags present in `index.html`

**Depends on:** none
**Time estimate:** 3min

---

### T002: Add .prose scoped CSS to style block
**File:** `index.html:467` (insert before closing `</style>`)
**Scope:** mpga-plugin
**Execution:** parallel (independent of T001)
**Risk:** Complexity=1 Uncertainty=1 Impact=1 → Score=1 (LOW)
**Critical path:** no
**Phase:** 1
**Evidence expected:**
- [E] `index.html:7–467` — `<style>` block, `.prose` class name confirmed absent by grep
- [E] `index.html:8-20` — CSS custom properties (light-only theme, `color: inherit` is safe)

**Acceptance criteria:**
- [ ] `.prose` CSS rules present in `<style>` block
- [ ] `h1/h2/h3` all render at `font-size: 1em` (not browser-default huge)
- [ ] `h2` has `border-bottom: 1px solid #e5e7eb`
- [ ] `.prose img { max-width: 100%; height: auto; }` present
- [ ] Test: `test_markdown_rendering.py` asserts `.prose` class rules present in `index.html`

**Depends on:** none
**Time estimate:** 3min

---

### T003: Add renderMarkdown() and stripMarkdown() utility functions **[CRITICAL PATH]**
**File:** `index.html:590` (insert after `safe()` function closing brace)
**Scope:** mpga-plugin
**Execution:** serial
**Risk:** Complexity=2 Uncertainty=1 Impact=2 → Score=4 (LOW)
**Critical path:** yes
**Phase:** 1
**Evidence expected:**
- [E] `index.html:582-590` — `safe()` function, insertion point confirmed
- [E] `index.html:529` — inline `<script>` block, no existing `renderMarkdown` or `stripMarkdown`

**Acceptance criteria:**
- [ ] `renderMarkdown(text)` defined: returns `DOMPurify.sanitize(marked.parse(text || ''))`
- [ ] `renderMarkdown(text)` falls back to `safe(text)` with HTML escaping if `marked` undefined
- [ ] `stripMarkdown(md)` defined: creates temp div, parses via `marked`, returns `textContent`
- [ ] `stripMarkdown(md)` falls back to `safe(md)` if `marked` undefined
- [ ] `renderMarkdown('## Hello')` returns string containing `<h2>`
- [ ] `stripMarkdown('## Hello\n**bold**')` returns `Hello bold` (no Markdown chars)
- [ ] Test: `test_markdown_rendering.py` asserts both function definitions present in `index.html`

**Depends on:** T001
**Time estimate:** 5min

---

### T004: Add .prose class to modal content container element
**File:** `index.html:517`
**Scope:** mpga-plugin
**Execution:** parallel (can run with T003)
**Risk:** Complexity=1 Uncertainty=1 Impact=1 → Score=1 (LOW)
**Critical path:** no
**Phase:** 1
**Evidence expected:**
- [E] `index.html:517` — `<div id="task-modal-content" class="modal-content-block">` element
- [E] `index.html:567` — `taskModalContent = getElementById("task-modal-content")` JS reference

**Acceptance criteria:**
- [ ] `id="task-modal-content"` element has `prose` added to its `class` attribute
- [ ] Element class is `modal-content-block prose` (or equivalent)
- [ ] Test: `test_markdown_rendering.py` asserts `task-modal-content` element has `prose` class

**Depends on:** T002
**Time estimate:** 2min

---

### T005: Modify renderModalContent() to render Markdown via innerHTML **[CRITICAL PATH]**
**File:** `index.html:658`
**Scope:** mpga-plugin
**Execution:** serial
**Risk:** Complexity=1 Uncertainty=1 Impact=3 → Score=3 (LOW)
**Critical path:** yes
**Phase:** 2
**Evidence expected:**
- [E] `index.html:655-659` — `renderModalContent()` full body, single `textContent` assignment to replace
- [E] `index.html:694` — `openTaskModal` caller confirmed
- [E] `index.html:729` — `openScopeModal` caller confirmed
- [E] `index.html:759` — `openMilestoneModal` caller confirmed

**Acceptance criteria:**
- [ ] Line 658 changed from `taskModalContent.textContent = ...` to `taskModalContent.innerHTML = renderMarkdown(...)`
- [ ] Empty state (`"-"`) still renders as the `emptyText` fallback (no Markdown parse on `-`)
- [ ] Opening a task with `## heading` in body shows `<h2>` in modal, not `## heading`
- [ ] Opening a task with `- [ ]` shows an unordered list item, not literal `- [ ]`
- [ ] Test: `test_markdown_rendering.py` asserts `innerHTML` and `renderMarkdown` appear in `renderModalContent`

**Depends on:** T003, T004
**Time estimate:** 5min

---

### T006: Modify renderTable() to strip Markdown from content columns
**File:** `index.html:957-965`
**Scope:** mpga-plugin
**Execution:** parallel (independent of T005)
**Risk:** Complexity=2 Uncertainty=2 Impact=2 → Score=8 (LOW)
**Critical path:** no
**Phase:** 2
**Evidence expected:**
- [E] `index.html:957-965` — column loop with `td.textContent = value` at line 960
- [E] `index.html:924` — `renderTable()` signature

**Acceptance criteria:**
- [ ] Markdown-bearing columns (`body`, `content`, `summary`, `notes`) pipe value through `stripMarkdown()` before `textContent` assignment
- [ ] Non-Markdown columns (IDs, statuses, priorities, titles) are unchanged
- [ ] Scope table Summary column shows `Overview This scope manages core config` not `## Overview\n**core config**`
- [ ] No `##`, `**`, `` ` ``, or `- [ ]` characters visible in any table cell
- [ ] Test: `test_markdown_rendering.py` asserts `stripMarkdown` call present in `renderTable` body

**Depends on:** T003
**Time estimate:** 5min

---

### T007: Modify renderTextBlock() to strip Markdown from body
**File:** `index.html:913`
**Scope:** mpga-plugin
**Execution:** parallel (independent of T005, T006)
**Risk:** Complexity=1 Uncertainty=1 Impact=1 → Score=1 (LOW)
**Critical path:** no
**Phase:** 2
**Evidence expected:**
- [E] `index.html:898-916` — `renderTextBlock()` full body, `p.textContent = body` at line 913

**Acceptance criteria:**
- [ ] `p.textContent = body` changed to `p.textContent = stripMarkdown(body)`
- [ ] Health and graph views display clean plain text without Markdown syntax
- [ ] Test: `test_markdown_rendering.py` asserts `stripMarkdown(body)` in `renderTextBlock`

**Depends on:** T003
**Time estimate:** 2min

---

## Risk Summary

| Task | Complexity | Uncertainty | Impact | Score | Level |
|------|:---:|:---:|:---:|:---:|:---:|
| T001 | 1 | 1 | 2 | 2 | LOW |
| T002 | 1 | 1 | 1 | 1 | LOW |
| T003 | 2 | 1 | 2 | 4 | LOW |
| T004 | 1 | 1 | 1 | 1 | LOW |
| T005 | 1 | 1 | 3 | 3 | LOW |
| T006 | 2 | 2 | 2 | 8 | LOW |
| T007 | 1 | 1 | 1 | 1 | LOW |

**HIGH RISK tasks:** none
**Average risk score:** 2.9
**Overall:** All tasks LOW risk. Single-file change with well-understood touch points.

---

## Critical Path

**Total estimated time:** ~13min
**Chain:** T001 → T003 → T005

```
T001 (3min) → T003 (5min) → T005 (5min)
     ↘
      T002 (3min) → T004 (2min) ↗ (also gates T005)
                         T006 (5min)  ← parallel
                         T007 (2min)  ← parallel
```

### Critical path tasks (delays here delay everything)
- T001: Add CDN script tags (3min)
- T003: Add utility functions (5min) — blocked by T001
- T005: Modify renderModalContent (5min) — blocked by T003 + T004

### Parallel lanes
- Lane A: T002 → T004 (can run while T001/T003 proceed)
- Lane B: T006 (can start once T003 done, parallel with T005)
- Lane C: T007 (can start once T003 done, parallel with T005, T006)

---

## Phase Breakdown

### Phase 1: Foundation — CDN + utilities + CSS
**Gate criteria:** `marked`, `DOMPurify` globals available; `renderMarkdown()` and `stripMarkdown()` defined; `.prose` CSS present; all verified by `test_markdown_rendering.py`
- T001, T002, T003, T004
- Estimated duration: ~8min
- Highest risk score: 4 (T003)

### Phase 2: Application — wire up all rendering surfaces
**Gate criteria:** No raw Markdown syntax visible in any modal, table cell, or text block; all acceptance criteria pass; `test_markdown_rendering.py` fully green
- T005, T006, T007
- Estimated duration: ~12min
- Highest risk score: 8 (T006)

---

## Open Questions
None. All design decisions approved in [DESIGN-markdown-rendering.md](DESIGN-markdown-rendering.md).
