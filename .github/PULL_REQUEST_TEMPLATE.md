## Summary

- 

## Safety impact

- [ ] This change is non-destructive.
- [ ] This change preserves dry-run by default.
- [ ] This change does not weaken `--execute`, `--yes`, or `--allow-live-root` guardrails.
- [ ] If cleanup behavior changed, bundle policy / Trash routing / operation-log behavior was considered.

## AI-first / zero-resident product boundary

- [ ] This change keeps cleanmac as an AI-first cleanup execution kernel, not a GUI/TUI retention app.
- [ ] This change does not add a GUI, TUI, menu bar app, LaunchAgent, LaunchDaemon, login item, background scanner, scheduler, or reminder loop.
- [ ] This change exposes machine-readable CLI/JSON/MCP contracts before any human-facing workflow polish.
- [ ] This change still runs only after explicit user/script/AI Host invocation and exits after the requested workflow.
- [ ] If the feature needs long-lived state, that state is represented as plans, review-selection files, reports, or operation logs instead of resident app memory.

## Validation

- [ ] `make quality-check`
- [ ] `make local-test`
- [ ] `make docs-smoke`
- [ ] `make governance-smoke`
- [ ] `make zero-resident-audit-smoke`
- [ ] `make security-smoke`
- [ ] `make release-check` or documented why Docker/full release validation was not available locally

## Documentation

- [ ] README.md updated when user-facing behavior changed.
- [ ] README.CN.md updated when user-facing behavior changed.
