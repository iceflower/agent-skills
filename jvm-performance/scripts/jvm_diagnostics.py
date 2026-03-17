#!/usr/bin/env python3
"""Collect JVM diagnostics from a running process.

Gathers GC stats, heap info, thread count, and VM flags using
jcmd, jstat, and jps from the JDK.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def find_jdk_tool(tool_name: str) -> Optional[str]:
    """Find a JDK tool on the system PATH or JAVA_HOME."""
    # Check PATH first
    path = shutil.which(tool_name)
    if path:
        return path

    # Check JAVA_HOME
    java_home = os.environ.get("JAVA_HOME", "")
    if java_home:
        candidates = [
            os.path.join(java_home, "bin", tool_name),
            os.path.join(java_home, "bin", f"{tool_name}.exe"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

    return None


def check_prerequisites() -> Dict[str, Optional[str]]:
    """Check for required JDK tools."""
    tools = {}
    for tool in ["jcmd", "jstat", "jps", "jinfo"]:
        tools[tool] = find_jdk_tool(tool)
    return tools


def run_command(
    cmd: List[str], timeout: int = 30
) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def get_gc_stats(jstat: str, pid: int) -> Dict[str, Any]:
    """Collect GC statistics using jstat."""
    result: Dict[str, Any] = {}

    # GC utilization
    rc, stdout, stderr = run_command([jstat, "-gcutil", str(pid)])
    if rc == 0 and stdout.strip():
        lines = stdout.strip().splitlines()
        if len(lines) >= 2:
            headers = lines[0].split()
            values = lines[1].split()
            gc_util = {}
            for h, v in zip(headers, values):
                try:
                    gc_util[h] = float(v)
                except ValueError:
                    gc_util[h] = v
            result["utilization"] = gc_util

    # GC counts and times
    rc, stdout, stderr = run_command([jstat, "-gc", str(pid)])
    if rc == 0 and stdout.strip():
        lines = stdout.strip().splitlines()
        if len(lines) >= 2:
            headers = lines[0].split()
            values = lines[1].split()
            gc_raw = {}
            for h, v in zip(headers, values):
                try:
                    gc_raw[h] = float(v)
                except ValueError:
                    gc_raw[h] = v
            result["raw"] = gc_raw

            # Extract key metrics
            ygc = gc_raw.get("YGC", 0)
            ygct = gc_raw.get("YGCT", 0)
            fgc = gc_raw.get("FGC", 0)
            fgct = gc_raw.get("FGCT", 0)
            gct = gc_raw.get("GCT", 0)

            result["summary"] = {
                "young_gc_count": ygc,
                "young_gc_time_sec": ygct,
                "full_gc_count": fgc,
                "full_gc_time_sec": fgct,
                "total_gc_time_sec": gct,
            }

    return result


def get_heap_info(jcmd: str, pid: int) -> Dict[str, Any]:
    """Collect heap information using jcmd."""
    result: Dict[str, Any] = {}

    rc, stdout, stderr = run_command([jcmd, str(pid), "GC.heap_info"])
    if rc == 0 and stdout.strip():
        result["heap_info_raw"] = stdout.strip()
        # Parse key numbers
        for line in stdout.splitlines():
            line = line.strip()
            if "used" in line.lower() and "capacity" in line.lower():
                result.setdefault("regions", []).append(line)

    return result


def get_vm_flags(jcmd: str, pid: int) -> Dict[str, Any]:
    """Collect VM flags using jcmd."""
    result: Dict[str, Any] = {}

    rc, stdout, stderr = run_command([jcmd, str(pid), "VM.flags"])
    if rc == 0 and stdout.strip():
        flags_line = ""
        for line in stdout.splitlines():
            if line.startswith("-") or line.strip().startswith("-"):
                flags_line += " " + line.strip()
            elif ":" in line and not line.startswith(str(pid)):
                continue
            else:
                flags_line += " " + line.strip()

        flags = flags_line.split()
        result["all_flags"] = flags

        # Extract key flags
        key_flags = {}
        for flag in flags:
            flag = flag.strip()
            for prefix in [
                "-XX:MaxHeapSize=", "-Xmx", "-XX:InitialHeapSize=", "-Xms",
                "-XX:MaxMetaspaceSize=", "-XX:MetaspaceSize=",
                "-XX:+Use", "-XX:-Use",
                "-XX:MaxRAMPercentage=", "-XX:InitialRAMPercentage=",
                "-XX:MaxGCPauseMillis=", "-XX:ParallelGCThreads=",
                "-XX:ConcGCThreads=", "-XX:G1HeapRegionSize=",
            ]:
                if flag.startswith(prefix):
                    key_flags[flag.split("=")[0] if "=" in flag else flag] = flag
                    break
        result["key_flags"] = key_flags

    return result


def get_thread_info(jcmd: str, pid: int) -> Dict[str, Any]:
    """Collect thread information."""
    result: Dict[str, Any] = {}

    # Try jcmd Thread.print for count
    rc, stdout, stderr = run_command([jcmd, str(pid), "Thread.print", "-l"], timeout=60)
    if rc == 0 and stdout.strip():
        thread_count = stdout.count('"')  # Each thread starts with a quoted name
        result["total_threads"] = thread_count

        # Count thread states
        states: Dict[str, int] = {}
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("java.lang.Thread.State:"):
                state = line.split(":", 1)[1].strip().split()[0]
                states[state] = states.get(state, 0) + 1
        if states:
            result["states"] = states
    else:
        # Fallback: count threads from /proc on Linux
        proc_path = f"/proc/{pid}/task"
        if os.path.isdir(proc_path):
            try:
                result["total_threads"] = len(os.listdir(proc_path))
            except OSError:
                pass

    return result


def get_vm_info(jcmd: str, pid: int) -> Dict[str, Any]:
    """Collect VM version and system properties."""
    result: Dict[str, Any] = {}

    rc, stdout, stderr = run_command([jcmd, str(pid), "VM.version"])
    if rc == 0 and stdout.strip():
        result["version"] = stdout.strip()

    rc, stdout, stderr = run_command([jcmd, str(pid), "VM.uptime"])
    if rc == 0 and stdout.strip():
        result["uptime"] = stdout.strip()

    return result


def detect_container_pid() -> Optional[int]:
    """Auto-detect Java PID in container (typically PID 1)."""
    # In containers, the main process is usually PID 1
    if os.path.isfile("/proc/1/cmdline"):
        try:
            with open("/proc/1/cmdline", "rb") as f:
                cmdline = f.read().decode("utf-8", errors="replace")
                if "java" in cmdline.lower():
                    return 1
        except OSError:
            pass

    # Try jps
    jps = find_jdk_tool("jps")
    if jps:
        rc, stdout, _ = run_command([jps, "-l"])
        if rc == 0:
            for line in stdout.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) >= 1 and parts[0].isdigit():
                    pid = int(parts[0])
                    if pid > 0:
                        return pid
    return None


def format_text_output(diagnostics: Dict[str, Any]) -> str:
    """Format diagnostics as human-readable text."""
    lines: List[str] = []
    sep = "=" * 60

    lines.append(sep)
    lines.append("JVM DIAGNOSTICS REPORT")
    lines.append(sep)

    pid = diagnostics.get("pid", "?")
    lines.append(f"Process ID: {pid}")

    # VM info
    vm_info = diagnostics.get("vm_info", {})
    if vm_info.get("version"):
        lines.append(f"JVM Version:\n  {vm_info['version']}")
    if vm_info.get("uptime"):
        lines.append(f"Uptime: {vm_info['uptime']}")

    # GC stats
    gc = diagnostics.get("gc_stats", {})
    if gc.get("summary"):
        lines.append(f"\n{'-' * 40}")
        lines.append("GC STATISTICS")
        lines.append(f"{'-' * 40}")
        s = gc["summary"]
        ygc = s.get("young_gc_count", 0)
        ygct = s.get("young_gc_time_sec", 0)
        fgc = s.get("full_gc_count", 0)
        fgct = s.get("full_gc_time_sec", 0)
        gct = s.get("total_gc_time_sec", 0)

        lines.append(f"  Young GC count:      {int(ygc)}")
        lines.append(f"  Young GC time:       {ygct:.3f}s")
        lines.append(f"  Full GC count:       {int(fgc)}")
        lines.append(f"  Full GC time:        {fgct:.3f}s")
        lines.append(f"  Total GC time:       {gct:.3f}s")

        if fgc and isinstance(fgc, (int, float)) and fgc > 10:
            lines.append(f"  ** WARNING: High Full GC count ({int(fgc)}) - investigate heap sizing **")

    if gc.get("utilization"):
        u = gc["utilization"]
        lines.append("\n  Heap Utilization:")
        for key in ["S0", "S1", "E", "O", "M", "CCS"]:
            val = u.get(key)
            if val is not None:
                label = {
                    "S0": "Survivor 0", "S1": "Survivor 1",
                    "E": "Eden", "O": "Old Gen",
                    "M": "Metaspace", "CCS": "Compressed Class",
                }.get(key, key)
                bar_len = int(float(val) / 5)
                bar = "#" * bar_len + "." * (20 - bar_len)
                lines.append(f"    {label:18s} [{bar}] {val:.1f}%")

    # Heap info
    heap = diagnostics.get("heap_info", {})
    if heap.get("heap_info_raw"):
        lines.append(f"\n{'-' * 40}")
        lines.append("HEAP INFO")
        lines.append(f"{'-' * 40}")
        lines.append(f"  {heap['heap_info_raw']}")

    # Thread info
    threads = diagnostics.get("thread_info", {})
    if threads:
        lines.append(f"\n{'-' * 40}")
        lines.append("THREAD INFO")
        lines.append(f"{'-' * 40}")
        total = threads.get("total_threads", "?")
        lines.append(f"  Total threads: {total}")
        states = threads.get("states", {})
        if states:
            for state, count in sorted(states.items(), key=lambda x: -x[1]):
                lines.append(f"    {state:30s} {count}")

    # VM flags
    flags = diagnostics.get("vm_flags", {})
    if flags.get("key_flags"):
        lines.append(f"\n{'-' * 40}")
        lines.append("KEY VM FLAGS")
        lines.append(f"{'-' * 40}")
        for _name, flag_str in sorted(flags["key_flags"].items()):
            lines.append(f"  {flag_str}")

    # Tool availability
    tools = diagnostics.get("tools", {})
    missing = [t for t, p in tools.items() if p is None]
    if missing:
        lines.append(f"\n{'-' * 40}")
        lines.append("MISSING TOOLS")
        lines.append(f"{'-' * 40}")
        for tool in missing:
            lines.append(f"  {tool}: not found (install a full JDK)")

    lines.append(f"\n{sep}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect JVM diagnostics from a running process.",
        epilog="Requires JDK tools (jcmd, jstat). Exit code 0 = success, 1 = error.",
    )
    parser.add_argument(
        "pid",
        nargs="?",
        type=int,
        default=None,
        help="PID of the Java process",
    )
    parser.add_argument(
        "--container",
        action="store_true",
        help="Auto-detect Java PID (typically PID 1 in containers)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output in JSON format for machine consumption",
    )

    args = parser.parse_args()

    # Determine PID
    pid = args.pid
    if pid is None and args.container:
        pid = detect_container_pid()
        if pid:
            print(f"Auto-detected Java PID: {pid}", file=sys.stderr)
        else:
            print("Error: Could not auto-detect Java process in container", file=sys.stderr)
            return 1
    elif pid is None:
        # Try to find any Java process
        jps = find_jdk_tool("jps")
        if jps:
            rc, stdout, _ = run_command([jps, "-l"])
            if rc == 0:
                java_procs = []
                for line in stdout.splitlines():
                    parts = line.strip().split(None, 1)
                    if len(parts) >= 1 and parts[0].isdigit():
                        p = int(parts[0])
                        name = parts[1] if len(parts) > 1 else ""
                        if p > 0 and "jps" not in name.lower():
                            java_procs.append((p, name))

                if len(java_procs) == 1:
                    pid = java_procs[0][0]
                    print(f"Auto-detected Java PID: {pid} ({java_procs[0][1]})", file=sys.stderr)
                elif len(java_procs) > 1:
                    print("Multiple Java processes found:", file=sys.stderr)
                    for p, name in java_procs:
                        print(f"  PID {p}: {name}", file=sys.stderr)
                    print("Specify PID as argument.", file=sys.stderr)
                    return 1

        if pid is None:
            parser.print_help()
            print("\nError: No PID specified and no Java process auto-detected.", file=sys.stderr)
            return 1

    # Check tools
    tools = check_prerequisites()

    if not any(tools.values()):
        system = platform.system().lower()
        if system == "darwin":
            hint = "Install a full JDK: brew install openjdk@21"
        elif system == "linux":
            hint = "Install a full JDK (e.g., sudo apt install openjdk-21-jdk)"
        elif system == "windows":
            hint = "Install a full JDK from https://adoptium.net/"
        else:
            hint = "Install a full JDK"

        print(
            f"Error: No JDK tools found on PATH or JAVA_HOME.\n"
            f"  {hint}\n"
            f"  Ensure JAVA_HOME is set and $JAVA_HOME/bin is on PATH.",
            file=sys.stderr,
        )
        return 1

    # Collect diagnostics
    diagnostics: Dict[str, Any] = {
        "pid": pid,
        "tools": {t: p for t, p in tools.items()},
    }

    jcmd = tools.get("jcmd")
    jstat = tools.get("jstat")

    if jcmd:
        diagnostics["vm_info"] = get_vm_info(jcmd, pid)
        diagnostics["heap_info"] = get_heap_info(jcmd, pid)
        diagnostics["vm_flags"] = get_vm_flags(jcmd, pid)
        diagnostics["thread_info"] = get_thread_info(jcmd, pid)
    else:
        print("Warning: jcmd not available - heap/flags/thread info will be limited", file=sys.stderr)
        diagnostics["vm_info"] = {}
        diagnostics["heap_info"] = {}
        diagnostics["vm_flags"] = {}
        diagnostics["thread_info"] = {}

    if jstat:
        diagnostics["gc_stats"] = get_gc_stats(jstat, pid)
    else:
        print("Warning: jstat not available - GC stats will be skipped", file=sys.stderr)
        diagnostics["gc_stats"] = {}

    # Output
    if args.json_output:
        # Clean up non-serializable tool paths for JSON
        clean_diag = dict(diagnostics)
        clean_diag["tools"] = {
            t: ("available" if p else "not found")
            for t, p in tools.items()
        }
        print(json.dumps(clean_diag, indent=2, default=str))
    else:
        print(format_text_output(diagnostics))

    return 0


if __name__ == "__main__":
    sys.exit(main())
