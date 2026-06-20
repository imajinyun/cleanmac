# Security Policy

`cleanmac` operates on local filesystem paths and includes commands that can delete files when explicit execution flags are provided. Please report security issues privately instead of opening a public issue.

## Supported versions

The project is currently pre-1.0. Security fixes are applied to the main development line.

| Version | Supported |
|---|---|
| `main` | Yes |
| `< 0.1.0` | No |

## Reporting a vulnerability

If you find a vulnerability, please report it privately to the maintainers. Include:

- Affected command and version or commit.
- Reproduction steps.
- Expected and actual behavior.
- Whether the issue can cause data loss, privilege escalation, path traversal, symlink escape, or unsafe deletion.

Do not include real private filesystem paths, credentials, tokens, or sensitive logs in public reports.

Preferred private channels are GitHub private vulnerability reporting on the repository security page or the security contact published in the package metadata. If neither is available in your checkout, open a minimal public issue asking for a private security contact without disclosing exploit details.

## Security-sensitive areas

- Path remapping with `--root` / `--home`.
- Symlink target validation.
- Live-root execution gates.
- `--execute`, `--yes`, `--allow-live-root`, and `--review-selection-file` behavior.
- Bundle allow/block policy.
- Trash routing and operation-log persistence.
- Dependency audit, generated `SBOM.json`, release checksums, and artifact attestation.

## AI and MCP Security

- **MCP Server Attack Surface**: The stdio MCP server (`scripts/cleanmac_mcp_server.py`)
  processes JSON-RPC requests from LLM clients. It does not expose a network socket.
- **Tool Definition Safety**: All 32 AI tools are read-only, planning, or dry-run by default;
  only `cleanmac_execute_plan` is destructive and requires explicit user confirmation.
- **Confirmation Token**: SHA-256 bound tokens prevent unauthorized plan execution.
- **Review Selection Constraint**: `cleanmac.review-selection.v1` files must match the source plan fingerprint before they can constrain dry-run or execution. Stale or mismatched selections fail closed with `SELECTION_VALIDATION_FAILED`.
- **Prompt Injection Prevention**: File and category names are treated as data,
  not instructions. MCP prompts include explicit guardrails against tool misuse.
- **Host Policy**: The `ai-host-policy` command defines machine-readable allow/deny
  rules for auto-call permissions, destructive execution gates, and error recovery.
