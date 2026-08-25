#!/usr/bin/env python3
"""Boot a dedicated Minecraft server with Advanced Backups and assert /backup start works."""

from __future__ import annotations

import argparse
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RCON_PASSWORD = "ab-harness"
READY_PATTERNS = (
    re.compile(r"Done \("),
    re.compile(r'For help, type ["\']help["\']'),
)
MOD_LOADED_PATTERN = re.compile(r"Config loaded!!")
BACKUP_COMPLETE_PATTERNS = (
    re.compile(r"Backup complete!"),
    re.compile(r"SAVING ENABLED - BACKUP COMPLETE!"),
)
BACKUP_FAILED_PATTERN = re.compile(r"ERROR MAKING BACKUP!")


class HarnessError(RuntimeError):
    pass


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def write_text(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def server_properties(game_port: int, rcon_port: int, password: str) -> str:
    return "\n".join(
        [
            "accepts-transfers=false",
            "allow-flight=false",
            "broadcast-console-to-ops=true",
            "broadcast-rcon-to-ops=true",
            "difficulty=peaceful",
            "enable-command-block=false",
            "enable-jmx-monitoring=false",
            "enable-query=false",
            "enable-rcon=true",
            "enable-status=false",
            "enforce-secure-profile=false",
            "enforce-whitelist=false",
            "force-gamemode=false",
            "function-permission-level=2",
            "gamemode=creative",
            "generate-structures=false",
            "hardcore=false",
            "hide-online-players=true",
            "level-name=world",
            "level-seed=harness",
            "level-type=minecraft:flat",
            "max-players=1",
            "max-tick-time=-1",
            "motd=AdvancedBackups harness",
            "online-mode=false",
            "op-permission-level=4",
            "pause-when-empty-seconds=86400",
            "player-idle-timeout=0",
            "pvp=false",
            f"rcon.password={password}",
            f"rcon.port={rcon_port}",
            f"server-port={game_port}",
            "simulation-distance=2",
            "spawn-animals=false",
            "spawn-monsters=false",
            "spawn-npcs=false",
            "spawn-protection=0",
            "sync-chunk-writes=false",
            "view-distance=2",
            "white-list=false",
            "",
        ]
    )


def backup_properties() -> str:
    return "\n".join(
        [
            "config.advancedbackups.enabled=true",
            "config.advancedbackups.save=true",
            "config.advancedbackups.togglesave=true",
            "config.advancedbackups.buffer=1048576",
            "config.advancedbackups.flush=false",
            "config.advancedbackups.activity=false",
            "config.advancedbackups.blacklist=session.lock,*_old",
            "config.advancedbackups.type=zip",
            "config.advancedbackups.path=./backups",
            "config.advancedbackups.frequency.min=0",
            "config.advancedbackups.frequency.max=24",
            "config.advancedbackups.frequency.uptime=true",
            "config.advancedbackups.frequency.schedule=1:00",
            "config.advancedbackups.frequency.shutdown=false",
            "config.advancedbackups.frequency.startup=false",
            "config.advancedbackups.frequency.delay=30",
            "config.advancedbackups.logging.clients=none",
            "config.advancedbackups.logging.clientfrequency=500",
            "config.advancedbackups.logging.console=true",
            "config.advancedbackups.logging.consolefrequency=500",
            "config.advancedbackups.zips.compression=1",
            "config.advancedbackups.chains.length=50",
            "config.advancedbackups.chains.compress=true",
            "config.advancedbackups.chains.smart=true",
            "config.advancedbackups.chains.maxpercent=50",
            "config.advancedbackups.purge.size=50",
            "config.advancedbackups.purge.days=0",
            "config.advancedbackups.purge.count=0",
            "config.advancedbackups.purge.incrementals=true",
            "config.advancedbackups.purge.incrementalchains=1",
            "",
        ]
    )


class MinecraftRcon:
    TYPE_RESPONSE = 0
    TYPE_COMMAND = 2
    TYPE_LOGIN = 3

    def __init__(self, host: str, port: int, password: str, timeout: float = 10.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.request_id = 0
        self._login(password)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def command(self, text: str) -> str:
        request_id = self._send(self.TYPE_COMMAND, text)
        reply_id, _, payload = self._recv()
        if reply_id != request_id:
            raise HarnessError(f"Unexpected RCON id {reply_id} for command {text!r}")
        return payload

    def _login(self, password: str) -> None:
        request_id = self._send(self.TYPE_LOGIN, password)
        reply_id, _, _ = self._recv()
        if reply_id == -1 or reply_id != request_id:
            raise HarnessError("RCON authentication failed")

    def _send(self, packet_type: int, payload: str) -> int:
        self.request_id += 1
        request_id = self.request_id
        body = struct.pack("<ii", request_id, packet_type) + payload.encode("utf-8") + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(body)) + body)
        return request_id

    def _recv(self) -> tuple[int, int, str]:
        length = struct.unpack("<i", self._recv_exact(4))[0]
        data = self._recv_exact(length)
        request_id, packet_type = struct.unpack("<ii", data[:8])
        payload = data[8:-2].decode("utf-8", errors="replace")
        return request_id, packet_type, payload

    def _recv_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            piece = self.sock.recv(size - len(chunks))
            if not piece:
                raise HarnessError("RCON connection closed")
            chunks.extend(piece)
        return bytes(chunks)


def wait_for_patterns(
    paths: list[Path],
    patterns: tuple[re.Pattern[str], ...],
    timeout: float,
    failed_pattern: re.Pattern[str] | None = None,
) -> str:
    deadline = time.time() + timeout
    last_text = ""
    while time.time() < deadline:
        chunks = [
            path.read_text(encoding="utf-8", errors="replace")
            for path in paths
            if path.exists()
        ]
        last_text = "\n".join(chunks)
        if failed_pattern and failed_pattern.search(last_text):
            raise HarnessError(f"Saw failure marker {failed_pattern.pattern}")
        if any(pattern.search(last_text) for pattern in patterns):
            return last_text
        time.sleep(0.5)
    raise HarnessError(
        f"Timed out after {int(timeout)}s waiting for {', '.join(pattern.pattern for pattern in patterns)}"
    )


def tail(text: str, lines: int = 80) -> str:
    return "\n".join(text.splitlines()[-lines:])


def connect_rcon(host: str, port: int, password: str, timeout: float) -> MinecraftRcon:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            return MinecraftRcon(host, port, password, timeout=8.0)
        except (OSError, HarnessError) as exc:
            last_error = exc
            time.sleep(1.0)
    raise HarnessError(f"Could not connect to RCON on {host}:{port}: {last_error}")


def stop_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            proc.kill()
        proc.wait(timeout=10)


def prepare_run_dir(run_dir: Path, game_port: int, rcon_port: int, password: str) -> None:
    write_text(run_dir / "eula.txt", "eula=true\n")
    write_text(run_dir / "server.properties", server_properties(game_port, rcon_port, password))
    write_text(run_dir / "config" / "AdvancedBackups.properties", backup_properties())


def build_core_and_mod(project_dir: Path, skip_build: bool) -> None:
    if skip_build:
        return
    core_jar = REPO_ROOT / "core" / "build" / "libs" / "advancedbackups-corelib.jar"
    if not core_jar.exists():
        print("Building core library...", flush=True)
        subprocess.run(["./gradlew", "shadowJar", "--no-daemon"], cwd=REPO_ROOT / "core", check=True)
    print(f"Compiling {project_dir.relative_to(REPO_ROOT)}...", flush=True)
    subprocess.run(["./gradlew", "compileJava", "--no-daemon"], cwd=project_dir, check=True)


def collect_backup_zips(run_dir: Path) -> list[Path]:
    backups = run_dir / "backups"
    if not backups.exists():
        return []
    return [
        path
        for path in backups.rglob("*.zip")
        if path.is_file() and "incomplete" not in path.name.lower()
    ]


def gradle_task_and_run_dir(loader: str, project_dir: Path) -> tuple[str, Path]:
    if loader == "fabric":
        return "runHarnessServer", project_dir / "run-harness"
    return "runServer", project_dir / "run" / "server"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loader", choices=("fabric", "neoforge"), default="fabric")
    parser.add_argument("--mc", default="26.1", help="Minecraft line directory, e.g. 26.1 or 26.2")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep-world", action="store_true", help="Do not wipe run-harness before start")
    parser.add_argument("--start-timeout", type=int, default=300)
    parser.add_argument("--backup-timeout", type=int, default=180)
    return parser.parse_args()


def dump_logs(log_paths: list[Path]) -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        for path in log_paths
    )
    if combined.strip():
        print("--- server log tail ---", file=sys.stderr)
        print(tail(combined), file=sys.stderr)


def main() -> int:
    args = parse_args()
    project_dir = REPO_ROOT / args.loader / args.mc
    if not project_dir.is_dir():
        raise HarnessError(f"Missing project directory {project_dir}")

    gradle_task, run_dir = gradle_task_and_run_dir(args.loader, project_dir)
    gradle_log = project_dir / "harness-gradle.log"
    game_port = find_free_port()
    rcon_port = find_free_port()
    proc: subprocess.Popen[bytes] | None = None
    log_paths = [gradle_log, run_dir / "logs" / "latest.log"]

    build_core_and_mod(project_dir, args.skip_build)

    if run_dir.exists() and not args.keep_world:
        subprocess.run(["rm", "-rf", str(run_dir)], check=True)
    prepare_run_dir(run_dir, game_port, rcon_port, DEFAULT_RCON_PASSWORD)

    print(
        f"Starting {args.loader} {args.mc} dedicated server on :{game_port} (RCON :{rcon_port})",
        flush=True,
    )
    with gradle_log.open("wb") as log_handle:
        proc = subprocess.Popen(
            ["./gradlew", gradle_task, "--no-daemon"],
            cwd=project_dir,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    try:
        try:
            wait_for_patterns(log_paths, (MOD_LOADED_PATTERN,), args.start_timeout)
            print("Advanced Backups loaded.", flush=True)
        except HarnessError:
            dump_logs(log_paths)
            raise HarnessError("Advanced Backups did not log 'Config loaded!!'") from None

        wait_for_patterns(log_paths, READY_PATTERNS, args.start_timeout)
        print("Server is ready. Triggering backup...", flush=True)

        rcon = connect_rcon("127.0.0.1", rcon_port, DEFAULT_RCON_PASSWORD, timeout=30)
        try:
            reply = rcon.command("backup start")
            print(f"RCON backup start -> {reply.strip() or '(no reply)'}", flush=True)
            wait_for_patterns(
                log_paths,
                BACKUP_COMPLETE_PATTERNS,
                args.backup_timeout,
                failed_pattern=BACKUP_FAILED_PATTERN,
            )
        finally:
            try:
                rcon.command("stop")
            except Exception:
                pass
            rcon.close()

        zips = collect_backup_zips(run_dir)
        if not zips:
            dump_logs(log_paths)
            raise HarnessError("Backup finished according to logs, but no zip was found under backups/")

        largest = max(zips, key=lambda path: path.stat().st_size)
        size = largest.stat().st_size
        if size < 256:
            raise HarnessError(f"Backup zip is too small: {largest} ({size} bytes)")

        print(f"PASS: {largest.relative_to(run_dir)} ({size} bytes)", flush=True)
        return 0
    except HarnessError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        dump_logs(log_paths)
        return 1
    finally:
        if proc is not None:
            stop_process(proc)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: command exited {exc.returncode}: {exc.cmd}", file=sys.stderr)
        sys.exit(exc.returncode)
