# Design: Markdown Rendering in MPGA Console

## Problem

The MPGA Console (a vanilla JS SPA served from a single `index.html` with no build toolchain) displays raw Markdown as literal text in all content areas. Task bodies, scope descriptions, milestone summaries, and notes containing Markdown headings, lists, code blocks, and links appear as unformatted strings. Users cannot read structured content.

**Fix:** Render Markdown as sanitized HTML inside modals; strip Markdown to plain text in table cells and text blocks.

## Constraints

- Single-file vanilla JS SPA with no build toolchain [E] `index.html`
- App is local-only, no public-facing deployment [E] `flask_app.py:1-5`
- No existing CDN script dependencies — confirmed by grep
- `safe()` function is a type coercer only (null/undefined to empty string), not an HTML escaper [E] `index.html:582-589`
- Single modal body path via `renderModalContent` [E] `index.html:655-659` called by three consumers: `openTaskModal` [E] `index.html:694`, `openScopeModal` [E] `index.html:729`, `openMilestoneModal` [E] `index.html:759`
- Table cell rendering concentrated in `renderTable` [E] `index.html:957-960`
- Text block rendering in `renderTextBlock` [E] `index.html:898-915`
- `.prose` CSS class name has no existing collision — confirmed by grep

## Alternatives Considered

### Option A: CDN libraries (marked.js + DOMPurify) with scoped utilities (SELECTED)

Add two CDN `<script>` tags for `marked.js` (~40KB) and `DOMPurify`. Define two utility functions inline: `renderMarkdown(text)` for HTML output with sanitization, and `stripMarkdown(md)` for plain-text extraction. Apply `renderMarkdown` in modals, `stripMarkdown` in table cells and text blocks. Scope rendered HTML styling under a `.prose` CSS class on the modal content container.

- **Pros:** Minimal touch points (3 functions modified), graceful fallback if CDN unavailable, clear separation between render and strip paths, no build toolchain changes.
- **Cons:** Two new CDN dependencies, ~40KB additional page weight.

### Option B: Patch `safe()` function to include Markdown rendering

Modify the existing `safe()` null-coercer to also parse Markdown, making every call site automatically render Markdown.

- **Pros:** Zero new call sites to update.
- **Cons:** Violates SRP — `safe()` is a type coercer used at 40+ call sites [E] `index.html:582-589`. Overloading it with Markdown concerns forces a full audit of every caller. Renders Markdown in places where plain text is expected (table cells, attributes). High risk of XSS if sanitization is missed at any call site.

### Option C: Server-side Markdown rendering in Flask

Add a Python Markdown library to Flask, render HTML server-side, return pre-rendered HTML from API endpoints.

- **Pros:** No client-side library needed.
- **Cons:** Adds Python dependency (`markdown` or `mistune`). Requires network round-trip per modal open. Introduces dual sanitization surfaces (server and client). Breaks offline usability. Changes API contract for all consumers.

## Decision Matrix

| Alternative | Complexity (1-5) | Risk (1-5) | Scope (1-5) | Reversibility (1-5) | Team impact (1-5) | **Total** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| **A: CDN + scoped utils** | 1 | 1 | 1 | 5 | 1 | **9** |
| B: Patch `safe()` | 3 | 4 | 4 | 3 | 3 | **17** |
| C: Server-side Flask | 4 | 3 | 4 | 2 | 3 | **16** |

**Scoring:** Complexity, Risk, Scope, Team impact -- lower is better. Reversibility -- higher is better.

## Decision

**Option A: CDN libraries with scoped utilities.** Lowest complexity, lowest risk, smallest scope, fully reversible (remove two script tags and two functions to revert). Option B scores 8 points worse due to SRP violation and call-site audit burden. Option C scores 7 points worse due to added server dependency and broken offline model.

## Consequences

- **Positive:**
  - Markdown content (headings, lists, code blocks, links) renders as formatted HTML in all modals.
  - Table cells and text blocks display clean plain text without Markdown syntax noise.
  - Graceful degradation: if CDN scripts fail to load, content falls back to escaped plain text with no breakage.
  - Scoped `.prose` CSS prevents style bleed into the rest of the application.

- **Negative:**
  - Two new external CDN dependencies (`marked.js`, `DOMPurify`).
  - ~40KB additional page weight on first load (cached thereafter).

- **Risks:**
  - CDN unavailability causes fallback to plain text (acceptable for a local-only app [E] `flask_app.py:1-5`).
  - Future Markdown features (e.g., tables, footnotes) may require `marked.js` configuration updates.

## Implementation Outline

1. **Add CDN script tags** to `index.html` `<head>`:
   - `marked.js` (latest stable, ~40KB)
   - `DOMPurify` (latest stable)

2. **Add two utility functions** to the inline `<script>` block:
   ```javascript
   function renderMarkdown(text) {
     if (typeof marked === 'undefined') return safe(text);
     return DOMPurify.sanitize(marked.parse(text || ''));
   }

   function stripMarkdown(md) {
     if (typeof marked === 'undefined') return safe(md);
     const tmp = document.createElement('div');
     tmp.innerHTML = marked.parse(md || '');
     return tmp.textContent || '';
   }
   ```

3. **Modify `renderModalContent`** [E] `index.html:655-659`:
   - Change `taskModalContent.textContent = text` to `taskModalContent.innerHTML = renderMarkdown(text)`
   - Add `.prose` class to the modal content container element

4. **Modify `renderTable`** [E] `index.html:957-960`:
   - Apply `stripMarkdown()` to Markdown-bearing columns: `body`, `content`, `summary`, `notes`
   - Continue using `textContent` assignment (no innerHTML in table cells)

5. **Modify `renderTextBlock`** [E] `index.html:898-915`:
   - Pipe `body` field through `stripMarkdown()` before `textContent` assignment

6. **Add `.prose` CSS** to the existing `<style>` block:
   ```css
   .prose { font-size: 0.9rem; line-height: 1.6; color: inherit; }
   .prose h1, .prose h2, .prose h3 { font-weight: 600; margin: 0.75em 0 0.25em; font-size: 1em; }
   .prose h2 { border-bottom: 1px solid #e5e7eb; padding-bottom: 0.2em; }
   .prose ul, .prose ol { padding-left: 1.25em; margin: 0.4em 0; }
   .prose li { margin: 0.2em 0; }
   .prose code { background: #f3f4f6; padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.85em; }
   .prose pre { background: #f3f4f6; padding: 0.75em 1em; border-radius: 4px; overflow-x: auto; }
   .prose p { margin: 0.4em 0; }
   .prose img { max-width: 100%; height: auto; }
   ```

## Open Questions

None. All design decisions have been explicitly approved.
