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
make mcp-smoke
make governance-smoke
make ai-governance-smoke
make ai-contract-smoke
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
- Keep `--yes`, `--allow-live-root`, budgets, skipped-item gates, bundle policy, Trash routing, operation logs, plan context checks, and review-selection constraints covered by tests when changing cleanup behavior.
- Prefer `--delete-mode trash` in examples that demonstrate real cleanup.
- Update both root summaries (`README.md`, `README.CN.md`) and detailed guides (`docs/doc/README.md`, `docs/doc/README.CN.md`) when user-facing commands, AI/MCP tools, schema contracts, or safety behavior changes.
- If a change bridges review output to execution (`review`, `--review-selection-file`, `policy-simulate`, or AI tool argv templates), document the source-fingerprint validation and fail-closed behavior.

## Pull request checklist

- [ ] The change is covered by tests.
- [ ] `make quality-check` passes.
- [ ] `make dependency-audit-smoke` passes for supply-chain changes.
- [ ] `make release-artifacts-smoke` passes for release, packaging, or manifest changes.
- [ ] `make docs-smoke` passes.
- [ ] `make mcp-smoke` passes (if MCP server touched).
- [ ] `make governance-smoke` passes.
- [ ] `make ai-governance-smoke` passes.
- [ ] `make ai-contract-smoke` passes.
- [ ] `make open-source-smoke` passes.
- [ ] `make security-smoke` passes when docs or examples mention destructive shell patterns.
- [ ] AGENTS.md is updated when project map, security rules, or build commands change.
- [ ] Documentation is updated in both English and Chinese when behavior changes.
- [ ] The change does not weaken destructive-operation guardrails.
