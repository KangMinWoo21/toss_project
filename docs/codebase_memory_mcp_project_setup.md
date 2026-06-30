# codebase-memory-mcp Project Setup

## Target

- GitHub URL: https://github.com/DeusData/codebase-memory-mcp
- Project root: `C:\Users\KangMinWoo\Documents\토스증권`

## Purpose

This setup is for Codex code exploration, impact-scope analysis, and token
savings. It is tooling preparation only.

It does not improve ML model performance, add trading features, enable live
trading, change strategy behavior, or change production readiness.

## Scope

The intended scope is the full project root, excluding paths and file types
listed in `.cbmignore`.

The ignore rules protect:

- secrets
- API keys
- account information
- large data files
- generated reports
- cache directories
- local index outputs
- dependency and build artifacts

## Required Exclusions

The project-level `.cbmignore` excludes `.env`, `.env.*`, `data/`, CSV files,
archives, PDFs, spreadsheets, parquet files, pickle/joblib artifacts, Python
and tool caches, `.git/`, codebase-memory output folders, dependencies, and
build outputs.

Do not open, summarize, index, commit, or print `.env` files, API keys, account
details, or brokerage credentials.

Do not index or summarize `data/` or report CSV contents.

## Safety Notes

- Production effect: none.
- Trading feature added: no.
- ML model output changed: no.
- Protected candidate changed: no.
- `trading_allowed=False` remains unchanged.
- Production/readiness/risk `BLOCK` must not be relaxed.
- Index results and cache directories must not be committed.
- Any `.codebase-memory/` or `graphify-out/` output remains local-only.

## Installation Status

Installation approval was granted after the initial setup commit.

Binary-only installation was completed from the upstream GitHub release:

- installed binary:
  `C:\Users\KangMinWoo\AppData\Local\Programs\codebase-memory-mcp\codebase-memory-mcp.exe`
- installed version: `codebase-memory-mcp 0.8.1`
- checksum verification: passed
- agent configuration: not run
- MCP/Codex configuration change: not performed
- indexing: not performed
- PATH modification: not performed by this setup

The upstream installer supports `--skip-config`, but the install script can also
modify the user PATH. To keep this setup narrow, the release archive and
`checksums.txt` were downloaded directly, verified, extracted, and copied to
the install directory without running the agent configuration step.

Future configuration or indexing still requires separate user approval.

If reinstalling or updating later, review the upstream release instructions
again before any network download or package install command is run.

Potential source checkout command used only for upstream instruction review:

```powershell
git clone https://github.com/DeusData/codebase-memory-mcp
```

Additional package-manager commands may be available for the repository, but
they must be checked against upstream documentation in a separate approved step
before execution.

Risks to review before installation:

- network download of third-party code
- package install scripts
- local MCP/Codex configuration changes
- unintended indexing of secrets or large data
- generated cache or graph output accidentally committed

## Safe Initialization Policy

Do not run indexing, fetch, API, or MCP/Codex configuration commands as part of
this preparation.

If the tool is later installed and supports dry-run or safe-init behavior, run
it only after confirming it respects `.cbmignore`, does not inspect excluded
files, and writes generated output only to ignored local cache directories.

## Safe Index Status

Safe index approval was granted after binary-only installation.

The installed binary was verified as `codebase-memory-mcp 0.8.1`. The tool help
does not expose an `index_repository` dry-run mode, so the setup first checked
that `auto_index=false`, confirmed there were no indexed projects, verified the
required `.cbmignore` patterns, and reviewed the local upstream source for
`.cbmignore` loading during discovery.

Because the native Windows CLI argument path did not accept the Korean project
path reliably, a local ASCII junction was created:

- junction path: `C:\tmp\toss-cbm-project`
- target path: `C:\Users\KangMinWoo\Documents\토스증권`

The project was indexed via the junction using:

```powershell
codebase-memory-mcp cli index_repository '{"repo_path":"C:/tmp/toss-cbm-project","mode":"fast"}'
```

Index result:

- project name: `C-tmp-toss-cbm-project`
- root path recorded by the tool: `C:/tmp/toss-cbm-project`
- nodes: `2440`
- edges: `10175`
- discovered files: `113`
- excluded directories included `.git`, `data`, and Python cache folders
- artifact present in project root: `false`

Local output:

- cache database:
  `C:\Users\KangMinWoo\.cache\codebase-memory-mcp\C-tmp-toss-cbm-project.db`
- config database:
  `C:\Users\KangMinWoo\.cache\codebase-memory-mcp\_config.db`

No `.codebase-memory/` or `graphify-out/` directory was created in the project
root. Local git exclude rules were added to `.git/info/exclude` for
`.codebase-memory/` and `graphify-out/`; these rules are local-only and are not
committed.

Post-index read-only graph checks returned zero `File` rows for:

- paths starting with `data/`
- paths containing `.env`
- paths ending with `.csv`, `.pdf`, `.xlsx`, `.zip`, `.parquet`, `.pkl`, or
  `.joblib`

MCP/Codex configuration remains disconnected. PATH remains unchanged.
