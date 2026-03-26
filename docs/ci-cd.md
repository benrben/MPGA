# MPGA + CI/CD

Run evidence health checks in CI to prevent documentation drift from reaching main.

## GitHub Actions

Copy the workflow from `mpga-plugin` to your project:

```bash
cp path/to/mpga-plugin/../.github/workflows/mpga.yml .github/workflows/
```

Or create it manually:

```yaml
# .github/workflows/mpga.yml
name: MPGA Evidence Check

on:
  pull_request:
    paths:
      - 'src/**'
      - 'MPGA/**'

jobs:
  evidence:
    name: Evidence health check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install MPGA CLI
        run: pip install -e mpga-plugin/

      - name: Verify evidence links
        run: bash mpga-plugin/bin/mpga.sh evidence verify

      - name: Check drift threshold
        run: bash mpga-plugin/bin/mpga.sh drift --ci --threshold 80

      - name: Check evidence coverage
        run: bash mpga-plugin/bin/mpga.sh evidence coverage --min 20

      - name: Health report (on failure)
        if: failure()
        run: bash mpga-plugin/bin/mpga.sh health --verbose
```

## GitLab CI

```yaml
# .gitlab-ci.yml
mpga-evidence:
  stage: test
  image: python:3.11
  script:
    - pip install -e mpga-plugin/
    - bash mpga-plugin/bin/mpga.sh evidence verify
    - bash mpga-plugin/bin/mpga.sh drift --ci --threshold 80
  rules:
    - changes:
        - src/**/*
        - MPGA/**/*
```

## Bitbucket Pipelines

```yaml
# bitbucket-pipelines.yml
pipelines:
  pull-requests:
    '**':
      - step:
          name: MPGA Evidence Check
          image: python:3.11
          script:
            - pip install -e mpga-plugin/
            - bash mpga-plugin/bin/mpga.sh evidence verify
            - bash mpga-plugin/bin/mpga.sh drift --ci --threshold 80
```

## Pre-commit hook

Run a quick drift check before every commit:

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
if [ -f "mpga-plugin/bin/mpga.sh" ]; then
  bash mpga-plugin/bin/mpga.sh drift --quick
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

Or with [pre-commit](https://pre-commit.com/):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: mpga-drift
        name: MPGA drift check
        entry: bash mpga-plugin/bin/mpga.sh drift --quick
        language: system
        pass_filenames: false
```

## Exit codes

| Command | Exit 0 | Exit 1 |
|---------|--------|--------|
| `mpga drift --ci` | Health ≥ threshold | Health < threshold |
| `mpga evidence coverage --min N` | Coverage ≥ N% | Coverage < N% |
| `mpga evidence verify` | All links valid | Any link stale |

## Thresholds

Configure in `MPGA/mpga.config.json`:

```json
{
  "drift": {
    "ciThreshold": 80
  },
  "evidence": {
    "coverageThreshold": 0.20
  }
}
```

Or override at call time:

```bash
mpga drift --ci --threshold 90       # Stricter
mpga evidence coverage --min 30      # Stricter coverage
```

## Auto-sync on merge

Optionally regenerate the knowledge layer after merging to main:

```yaml
# .github/workflows/mpga-sync.yml
name: MPGA Sync

on:
  push:
    branches: [main]
    paths: ['src/**']

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Sync MPGA knowledge layer
        run: |
          pip install -e mpga-plugin/
          bash mpga-plugin/bin/mpga.sh sync --incremental

      - name: Commit updated knowledge layer
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: sync MPGA knowledge layer [skip ci]"
          file_pattern: "MPGA/**"
```
