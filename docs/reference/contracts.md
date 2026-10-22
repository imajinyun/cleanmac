# App cache and log contracts

cleanmac is an AI-first, zero-resident macOS cleanup CLI and MCP-ready execution kernel. These capabilities run only after an explicit invocation and exit when the workflow completes. Discovery and review are read-only; cleanup defaults to dry-run.

## Discovery categories

| Category | Scope |
| --- | --- |
| `userCache` | User Library caches, subject to shared application activity and data protection |
| `userAppCache` | Application Container caches and temporary files; protected Apple containers remain excluded |
| `appSupportCaches` | Exact Chromium/Electron cache subtrees under user Application Support |
| `browserServiceWorkerCaches` | Per-origin Service Worker `CacheStorage/<origin>/<cache>` dirs from a bounded browser-profile allowlist |
| `automationBrowserCaches` | Rebuildable Puppeteer browser downloads under `~/.cache/puppeteer` |
| `chrome`, `edge`, `brave`, `arc`, `firefox`, `safari`, `chromium`, `opera`, `vivaldi`, `dia`, `orion`, `zen`, `yandex`, `helium`, `comet`, `qqBrowser3`, `vscode`, `aiToolCaches`, `feishu` | Application-specific browser/editor cache rules, sharing the same path activity checks |
| `dropbox`, `baiduNetdisk`, `teambitionDisk`, `box`, `googleDrive`, `onedrive` | Cloud-drive regenerable cache leaves; synced folders and account state stay protected |
| `microsoftOffice`, `microsoftOutlook`, `iwork`, `wps`, `thunderbird`, `mailCache` | Office, suite, and mail regenerable cache leaves; documents, mailboxes, and preferences stay protected |
| `chromeOldVersions`, `edgeOldVersions`, `braveOldVersions` | Superseded `Contents/Frameworks/.../Versions/<old>` dirs inside `/Applications` and `~/Applications` bundles; `Current` target and newer staged updates preserved |
| `edgeUpdaterPayloads` | Staged `Microsoft/EdgeUpdater/apps/msedge-stable/<version>` payloads older than the installed Edge; keep-newest fallback when the installed version is unreadable |
| `userLogs` | Explicitly selected user Library logs; canonical `Logs` and legacy `logs` roots are deduplicated |

`appSupportCaches` discovers Code Cache, GPU, shader, Dawn, completed Crashpad, CRX download, and exact Service Worker `CacheStorage` directories. Ambiguous `Cache` and `CachedData` directories require a recognized application or a physical regenerable cache marker. Symlinked application roots, cache roots, Library ancestors, and markers do not establish discovery authority. The generic route inherits applicable application-specific protection rules, including Claude's storage state. Entire app directories, Service Worker databases (`ScriptCache` is never discovered by any category), local storage, login data, cookies, credentials, and sessions are not generic cache targets.

Service Worker storage is bounded and split by risk. `ScriptCache` (extension/worker bytecode) is never discovered by any category. For the browser-specific categories (`chrome`, `edge`, `brave`, `arc`), `Service Worker/CacheStorage` stays enumerated as visible but locked review evidence (`app-protected-data`) and cannot be deleted through those categories. Actual reclaim is opt-in only: the advanced, non-default, non-recommended `browserServiceWorkerCaches` enumerates only the depth-2 `Service Worker/CacheStorage/<origin>/<cache>` directories under a fixed allowlist of Chromium-family profile roots (Chrome, Edge, Brave, Arc, Vivaldi, Dia, Opera), rejects symlinked storage/origin/cache entries, and preserves origins whose on-disk name embeds a protected offline web editor or PWA domain (Google Workspace, GitHub, GitLab, Figma, Notion, Linear, Photopea, Pixlr, CapCut, CodePen, CodeSandbox, Replit, StackBlitz, Excalidraw). A path outside the provider allowlist is skipped as `outside-provider-allowlist`.

Old browser builds are pruned as whole directories, not cache leaves. `chromeOldVersions`, `edgeOldVersions`, and `braveOldVersions` read the framework `Versions/Current` symlink, keep its target and the single physical version directory with a greater mtime (a staged auto-update), and enumerate the remaining physical version directories under `/Applications` and `~/Applications`. `edgeUpdaterPayloads` reads `CFBundleShortVersionString` from the installed Edge `Info.plist` and enumerates only strictly older payloads; without a readable installed version it requires at least two payload directories and keeps the newest. Both providers fail closed on a missing, dangling, or symlink-escaping marker, reject symlinked version directories, carry the browser process guards, and are advanced, non-default, and non-recommended; plan replay re-validates every path and rejects anything outside these shapes as `outside-provider-allowlist`.

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
