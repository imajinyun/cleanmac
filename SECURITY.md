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
- `--execute`, `--yes`, and `--allow-live-root` behavior.
- Bundle allow/block policy.
- Trash routing and operation-log persistence.
- Dependency audit, generated `SBOM.json`, release checksums, and artifact attestation.
