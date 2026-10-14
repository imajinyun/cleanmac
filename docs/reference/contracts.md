# App cache and log contracts

cleanmac is an AI-first, zero-resident macOS cleanup CLI and MCP-ready execution kernel. These capabilities run only after an explicit invocation and exit when the workflow completes. Discovery and review are read-only; cleanup defaults to dry-run.

## Discovery categories

| Category | Scope |
| --- | --- |
| `userCache` | User Library caches, subject to shared application activity and data protection |
| `userAppCache` | Application Container caches and temporary files; protected Apple containers remain excluded |
| `appSupportCaches` | Exact Chromium/Electron cache subtrees under user Application Support |
| `automationBrowserCaches` | Rebuildable Puppeteer browser downloads under `~/.cache/puppeteer` |
| `chrome`, `edge`, `vscode`, `aiToolCaches`, `feishu` | Existing application-specific cache rules, sharing the same path activity checks |
| `userLogs` | Explicitly selected user Library logs; canonical `Logs` and legacy `logs` roots are deduplicated |

`appSupportCaches` discovers Code Cache, GPU, shader, Dawn, completed Crashpad, CRX download, and Service Worker CacheStorage/ScriptCache directories. Ambiguous `Cache` and `CachedData` directories require a recognized application or a physical regenerable cache marker. Symlinked application roots, cache roots, Library ancestors, and markers do not establish discovery authority. The generic route inherits applicable application-specific protection rules, including Claude's storage state. Entire app directories, Service Worker databases, local storage, login data, cookies, credentials, and sessions are not generic cache targets.

## Application activity

All cleanup categories share path ownership checks. A broad cache candidate containing an application's cache receives the application's protection, even when an application-specific category was not selected. A scan lazily reads one `ps -axo comm=` executable snapshot, including recognized helper names and app bundle paths. It does not read process arguments. An unavailable observation yields `process-state-unknown`; a matching executable yields `app-running`. Both preserve the candidate.

Execution observes activity again before every candidate deletion. An application starting after preview can therefore turn the candidate into an audited skip. `CLEANMAC_TEST_MODE=1` or `CLEANMAC_TEST_NO_AUTH=1` disables host process observations. This is a test boundary, not a production execution option for overriding activity protection.

## Review handoff

`cleanmac.inspect.v1`, `cleanmac.plan.v1`, and `cleanmac.clean.v1` retain executable candidates separately from `skipped` evidence. Plans retain the skips in `pre_clean_report.skipped` and at the plan root. `cleanmac.review.v1` merges that evidence into its item list without renumbering existing candidate IDs.

Skipped policy items expose `application`, `reason`, `protected: true`, `locked: true`, `selectable: false`, and `default_selected: false`. Their review evidence explains the preservation rule. `cleanmac.review-selection.v1` rejects a protected ID even if a caller edits the selection file. Items excluded only by an existing review selection remain excluded and can be reconsidered through a fresh source plan.

The source fingerprint is bound to the complete source payload. A selection file is a constraint input and must accompany its source plan. Root/home, confirmation-token, Trash routing, execution budget, and operation-log gates continue to apply.

## Space accounting

Candidates from overlapping categories are normalized into disjoint paths before filtering or selection. Broad parent candidates are split around narrower targets, preserving uncovered siblings. Exact duplicate paths prefer the specific category. Recursive inspection retains hierarchy rows, but category, file type, directory, and selection totals allocate nested space only once. Separate symlinks retain separate identities and account for the links themselves. Directory metadata is not added to the sum of file content sizes. These are logical-byte estimates, not APFS physical block reclamation guarantees.

`selection_accounting` distinguishes `discovered_count/bytes`, `protected_count/bytes`, `selectable_count/bytes`, and `selected_count/bytes`. Review selection summaries expose the corresponding byte totals. `total_bytes` and plan `estimated_reclaimable_bytes` describe the filtered candidates; protected items do not inflate execution budgets.

## Read-only invocation examples

```bash
python3 cleanmac.py --json clean inspect --categories userCache,userAppCache,appSupportCaches,automationBrowserCaches,chrome,edge,vscode,aiToolCaches,feishu --limit 200
python3 cleanmac.py --json clean inspect --categories userLogs --older-than-days 7 --limit 200
```

Generate a plan, review its selected and locked items, then pass the matching plan and review selection to the existing dry-run workflow. Real execution continues to require explicit execution and applicable confirmation gates; this discovery contract does not grant automatic execution authority.
