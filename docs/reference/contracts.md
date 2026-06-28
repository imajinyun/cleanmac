# cleanmac Contract Reference

This reference records the machine-readable contracts that cleanmac expects AI
Hosts, MCP clients, release gates, and aiflow workflows to preserve.

## Product Boundary

cleanmac is an AI-first, zero-resident macOS cleanup CLI. It runs only when a
user, script, or AI Host explicitly invokes it, then exits after the requested
workflow. The product boundary forbids GUI/TUI retention surfaces, menu bar
processes, daemons, login items, background scanners, unsolicited reminders, and
idle CPU or memory use.

Core boundary schemas:

- `cleanmac.zero-resident.v1`
- `cleanmac.zero-resident-audit.v1`
- `cleanmac.no-disturbance.v1`
- `cleanmac.product-surface-drift-audit.v1`
- `cleanmac.runtime-lifecycle-policy.v1`

Primary gates:

- `make zero-resident-audit-smoke`
- `make no-disturbance-smoke`
- `make ai-first-release-checklist-smoke`

## Cleanup Execution

Cleanup is dry-run-first. Real deletion must preserve the governed execution
chain:

1. Generate or inspect candidates.
2. Produce a plan.
3. Normalize the plan through review.
4. Apply review-selection constraints.
5. Validate plan context before replay.
6. Use Trash routing unless a policy explicitly allows another mode.
7. Require matching confirmation tokens for destructive AI/MCP calls.
8. Write operation-log evidence.

Deletion primitives are owned by `cleancli/delete_ops.py`; business modules must
not call `rm`, `sudo rm`, Finder deletion, AppleScript deletion, `shutil.rmtree`,
`shutil.move`, or direct `.unlink()` as cleanup exits.

Core execution schemas:

- `cleanmac.clean.v1`
- `cleanmac.plan-policy.v1`
- `cleanmac.validate-plan.v1`
- `cleanmac.execute-gate.v1`
- `cleanmac.review.v1`
- `cleanmac.review-selection.v1`
- `cleanmac.operation-log-entry.v1`
- `cleanmac.operation-log-status.v1`

Primary gates:

- `make local-test`
- `make governed-execution-smoke`
- `make macos-smoke`

## AI Host and MCP

AI Hosts should start from stable JSON and MCP contracts instead of ad hoc shell
commands. The recommended discovery chain is:

1. `cleanmac --json capabilities`
2. `cleanmac --json ai-host-integration-pack`
3. `cleanmac --json ai-host-preflight`
4. `cleanmac --json ai-host-evidence`
5. MCP meta, resource, prompt, and tool indexes
6. `cleanmac --json ai-workflow`

Destructive MCP tools must deny auto-call and require confirmation. The MCP
server must not accept raw shell command input; tool calls must resolve to
structured argv templates.

Core AI/MCP schemas:

- `cleanmac.ai-entrypoint-contract.v1`
- `cleanmac.ai-workflow.v1`
- `cleanmac.ai-safety-chain.v1`
- `cleanmac.ai-host-policy.v1`
- `cleanmac.ai-host-preflight.v1`
- `cleanmac.ai-host-evidence.v1`
- `cleanmac.ai-host-integration-pack.v1`
- `cleanmac.ai-host-tool-call-decision.v1`
- `cleanmac.ai-schema-registry.v1`
- `cleanmac.mcp-meta-index.v1`
- `cleanmac.mcp-resource-index.v1`
- `cleanmac.mcp-prompt-index.v1`
- `cleanmac.mcp-tool-index.v1`
- `cleanmac.mcp-surface-audit.v1`

Primary gates:

- `make ai-governance-smoke`
- `make ai-contract-smoke`
- `make mcp-smoke`
- `make ai-host-smoke`
- `make ai-robustness-smoke`

## Release and Supply Chain

Release evidence is contract-driven. Workflows and local gates should reuse the
same scripts for manifests, checksums, SBOM generation, and readiness evidence.

Core release schemas:

- `cleanmac.release-readiness.v1`
- `cleanmac.release-diagnostics.v1`
- `cleanmac.release-evidence.v1`
- `cleanmac.release-operator-summary.v1`
- `cleanmac.release-rehearsal.v1`
- `cleanmac.release-promotion-decision.v1`
- `cleanmac.release-rollback-plan.v1`
- `cleanmac.release-post-publish-verification.v1`
- `cleanmac.release-post-publish-result.v1`
- `cleanmac.release-post-publish-evidence-template.v1`
- `cleanmac.release-artifact-manifest.v1`

Primary gates:

- `make release-readiness-smoke`
- `make release-artifacts-smoke`
- `make open-source-smoke`
- `make dependency-audit-smoke`
- `make release-check`

## aiflow Workflow Policy

`aiflow.yaml` is the root-level aiflow source of truth for cleanmac workflow
orchestration. Keep the workflow policy in the repository root. Do not move or
duplicate it under `.aiflow/`.

The `.aiflow/` directory is local runtime space only. It may contain generated
run evidence, store files, lock files, scratch data, and temporary state. It
must not contain committed workflow policy, source code, release gates, or
project documentation.

The root `aiflow.yaml` defines the workspace boundary, command allowlist,
required acceptance commands, required context files, MCP provider entry,
command-approval policy, and security redaction rules.

The cleanmac aiflow flow is intentionally validation-first:

- Use project commands before adding custom harness tools.
- Keep destructive cleanup behind cleanmac's own review and execution gates.
- Keep aiflow commit and push disabled.
- Require approval for command tool use inside aiflow runs.
- Treat `.aiflow/` and historical `.harness/` directories as runtime state, not
  source.

Primary aiflow checks:

- `aiflow doctor -root .`
- `aiflow report -root . -fail-on-invalid`
- `aiflow advisory -root . -fail-on-not-ready`
