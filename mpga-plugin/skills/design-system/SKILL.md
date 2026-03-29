---
name: mpga-design-system
description: Build and maintain design tokens, component catalogs, and token compliance checks
---

## design-system

**Trigger:** The user wants to create a design system, extract tokens from existing styles, add a token, inspect component drift, or audit token compliance.

## Modes

### init
- Scan project CSS and style files
- Extract tokens
- Generate `MPGA/design-system/tokens.json`
- Generate `MPGA/design-system/tokens.css`

### add-token
- Add a token with `name`, `value`, and `category`
- Update both `tokens.json` and `tokens.css`

### catalog
- List the reusable components in `MPGA/design-system/COMPONENTS.md`
- Flag drift:
  - used but undocumented
  - documented but unused

### audit
- Find hardcoded values that should be tokenized
- Report compliance percentage

## Token format
Store categories in JSON:
- `color`
- `spacing`
- `typography`
- `breakpoint`

## Security
- Validate values against an allowlist before writing:
  - hex colors
  - px/rem/em values
  - font names
  - numeric-safe breakpoint values
- Reject dangerous values like `url()`, `expression()`, and `@import`.

## Output
- Updated `MPGA/design-system/tokens.json`
- Updated `MPGA/design-system/tokens.css`
- Component catalog output
- Compliance findings when auditing
