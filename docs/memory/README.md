# Agent memory

Persistent, file-based notes the Claude Code agent keeps for this project — one
fact per file, with YAML frontmatter (`name` / `description` / `metadata.type`).
`MEMORY.md` is the index that gets loaded into the agent's context each session;
every other `*.md` here is a single memory it can recall on demand.

## Why these live in the repo

The harness reads and writes agent memory from a per-project directory under the
user profile:

```
C:\Users\<user>\.claude\projects\M--claud-projects-steel-sim\memory
```

On this machine that path is a **Windows directory junction** pointing here, so
new memories the agent writes land directly in `docs/memory/` and are tracked by
git instead of drifting in an untracked profile folder. The repo is the single
source of truth.

To re-create the link on another machine (run once, paths are machine-specific):

```powershell
$link   = "$env:USERPROFILE\.claude\projects\M--claud-projects-steel-sim\memory"
$target = "M:\claud_projects\steel-sim\docs\memory"   # adjust to local clone path
if (Test-Path $link) { Remove-Item $link -Recurse -Force }
cmd /c mklink /J "$link" "$target"
```

The junction itself is local state and is **not** part of the repo — only the
`*.md` files are. A clone without the junction still has every memory; it just
won't be wired into that machine's harness until the command above is run.
