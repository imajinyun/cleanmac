# Contributing to cleanmac

Thank you for helping improve `cleanmac`. This project is a safety-first macOS cleanup CLI, so contributions must preserve the default dry-run behavior and the manual gates around destructive cleanup.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[dev,build]'
```

## Local validation

Before opening a pull request, run the fast checks:

```bash
make quality-check
make local-test
make dependency-audit-smoke
make docs-smoke
make governance-smoke
make open-source-smoke
```

For release-oriented changes, run the full gate when Docker is available:

```bash
make release-check
```

If Docker is not available locally, include that limitation in the pull request and make sure CI runs the Docker validation job.

## Safety expectations

- Keep cleanup dry-run by default.
- Do not add automation that runs `clean --execute` without explicit human action.
- Keep `--yes`, `--allow-live-root`, budgets, skipped-item gates, bundle policy, Trash routing, and operation logs covered by tests when changing cleanup behavior.
- Prefer `--delete-mode trash` in examples that demonstrate real cleanup.
- Update both `README.md` and `README.CN.md` when user-facing commands or safety behavior changes.

## Pull request checklist

- [ ] The change is covered by tests.
- [ ] `make quality-check` passes.
- [ ] `make dependency-audit-smoke` passes for supply-chain changes.
- [ ] `make docs-smoke` passes.
- [ ] `make governance-smoke` passes.
- [ ] `make open-source-smoke` passes.
- [ ] Documentation is updated in both English and Chinese when behavior changes.
- [ ] The change does not weaken destructive-operation guardrails.
