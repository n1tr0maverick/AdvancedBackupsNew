# Minecraft dedicated-server harness

Boots a headless Fabric or NeoForge dedicated server with Advanced Backups, runs `/backup start` over RCON, and checks that a zip backup is written.

This is an in-game environment test, not a unit test. It needs Java 25 (via the Gradle toolchain), network access to download Minecraft, and several minutes for first-time world generation.

## Usage

From the repository root:

```bash
python3 scripts/minecraft-harness/run_harness.py --loader fabric --mc 26.1
python3 scripts/minecraft-harness/run_harness.py --loader neoforge --mc 26.1
python3 scripts/minecraft-harness/run_harness.py --loader fabric --mc 26.2
```

Or `scripts/minecraft-harness/run.sh --loader fabric --mc 26.1`.

The script:

1. Builds `core` (if needed) and compiles the selected loader project
2. Prepares the run directory with `eula=true`, a flat offline world, RCON, and zip-backup config
3. Starts Fabric `runHarnessServer` or NeoForge `runServer`
4. Waits for `Config loaded!!` and `Done (`
5. Sends `backup start`, then `stop`
6. Asserts a non-empty zip exists under the run directory's `backups/` folder

## Options

| Flag | Meaning |
|------|---------|
| `--skip-build` | Do not compile; use the current project output |
| `--keep-world` | Reuse the run directory instead of wiping it |
| `--start-timeout` | Seconds to wait for the server to become ready (default 300) |
| `--backup-timeout` | Seconds to wait for backup completion (default 180) |

Gradle/server output is written to `<loader>/<mc>/harness-gradle.log`. Worlds and backups live in `fabric/<mc>/run-harness/` or `neoforge/<mc>/run/server/` (gitignored).
