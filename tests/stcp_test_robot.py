#!/usr/bin/env python3
"""STCP IETF test robot: reproducible checks with explicit PASS/FAIL/SKIP evidence.

Only IETF tests and read-only implementation inspection. Never builds or edits
the production kernel/SDK/Zephyr sources. Live checks require explicit opt-in.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--linux-source", type=Path, help="STCP repository root")
    p.add_argument("--zephyr-session", type=Path, help="Zephyr STCP Rust session.rs")
    p.add_argument("--live-linux", action="store_true", help="compile and run real AF_STCP TCP loopback")
    p.add_argument("--live-port", type=int, default=19533)
    p.add_argument("--live-repeat", type=int, default=100)
    p.add_argument("--external-zephyr-command", nargs="+", help="operator-provided real Zephyr interop test executable and arguments")
    p.add_argument("--external-zephyr-repeat", type=int, default=1)
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--report", type=Path, default=ROOT / "tests" / "robot-report.json")
    args = p.parse_args()
    if not (1 <= args.live_port <= 65535) or args.live_repeat < 1 or args.external_zephyr_repeat < 1 or args.timeout < 1:
        p.error("invalid port, repeat count or timeout")
    results = []
    def record(name, status, details, elapsed=0, category="offline"):
        results.append(dict(name=name, status=status, category=category, duration_seconds=round(elapsed, 3), details=details[-12000:]))
        print(f"[{status}] {name} ({elapsed:.2f}s)", flush=True)
        if status == "FAIL": print(details[-3000:], file=sys.stderr)
    def command(name, argv, timeout, env=None, category="offline"):
        start = time.monotonic()
        try:
            run = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, env=env, check=False)
            record(name, "PASS" if run.returncode == 0 else "FAIL", f"exit={run.returncode}\n{run.stdout}", time.monotonic()-start, category)
        except (OSError, subprocess.TimeoutExpired) as exc:
            record(name, "FAIL", str(exc), time.monotonic()-start, category)
    command("crypto-vectors", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_stcp_vectors.py", "-v"], args.timeout)
    xml = ROOT / "internet-draft/draft-paxsudos-stcp-00.xml"
    try:
        root = ET.parse(xml).getroot()
        if root.tag != "rfc" or root.attrib.get("version") != "3": raise ValueError("not RFCXML v3")
        record("rfcxml-parse", "PASS", "RFCXML v3 parsed")
    except Exception as exc:
        record("rfcxml-parse", "FAIL", str(exc))
    tool = shutil.which("xml2rfc")
    if tool:
        with tempfile.TemporaryDirectory(prefix="stcp-rfc-") as d:
            for kind in ("text", "html"):
                command("rfcxml-"+kind, [tool, "--"+kind, "--out", str(Path(d)/("draft."+("txt" if kind=="text" else "html"))), str(xml)], args.timeout)
    else:
        record("rfcxml-text", "SKIP", "xml2rfc executable not installed")
        record("rfcxml-html", "SKIP", "xml2rfc executable not installed")
    linux = args.linux_source
    if linux and (linux / "kernel/module/rust/src/session.rs").is_file():
        env = dict(os.environ, STCP_SOURCE=str(linux.resolve()))
        command("linux-source-contract", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_stcp_source_contract.py", "-v"], args.timeout, env)
    else:
        record("linux-source-contract", "SKIP", "supply --linux-source STCP_REPO_ROOT")
    z = args.zephyr_session
    if linux and z and (linux / "kernel/module/rust/src/session.rs").is_file() and z.is_file():
        command("handshake-source-and-model", [sys.executable, str(ROOT/"tests/test_handshake_boundary.py"), "--linux", str(linux/"kernel/module/rust/src/session.rs"), "--zephyr", str(z)], args.timeout)
    else:
        record("handshake-source-and-model", "SKIP", "supply both --linux-source and --zephyr-session")
    if args.live_linux:
        if not shutil.which("gcc"):
            record("linux-af-stcp-live", "FAIL", "gcc required for explicitly requested live test", category="live")
        else:
            with tempfile.TemporaryDirectory(prefix="stcp-live-") as d:
                exe = str(Path(d)/"loopback")
                command("linux-live-build", ["gcc", "-O2", "-Wall", "-Wextra", "-pthread", "-o", exe, str(ROOT/"tests/stcp_kernel_loopback.c")], args.timeout, category="live")
                if results[-1]["status"] == "PASS":
                    for i in range(args.live_repeat):
                        command(f"linux-af-stcp-live-{i+1:03d}", [exe, str(args.live_port)], args.timeout, category="live")
                        if results[-1]["status"] == "FAIL": break
    else:
        record("linux-af-stcp-live", "SKIP", "opt in with --live-linux; requires loaded module", category="live")
    if args.external_zephyr_command:
        for i in range(args.external_zephyr_repeat):
            command(f"zephyr-external-live-{i+1:03d}", args.external_zephyr_command, args.timeout, category="external-live")
            if results[-1]["status"] == "FAIL": break
    else:
        record("zephyr-external-live", "SKIP", "no real Zephyr test command supplied; no hardware run claimed", category="external-live")
    summary = {s: sum(r["status"] == s for r in results) for s in ("PASS", "FAIL", "SKIP")}
    report = dict(schema_version=1, timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(), scope="STCP IETF validation; skipped live tests are not evidence of interoperability", host_kernel=os.uname().release if hasattr(os,"uname") else None, source_paths=dict(linux=str(linux) if linux else None, zephyr=str(z) if z else None), summary=summary, tests=results)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    print("SUMMARY", summary, "REPORT", args.report, flush=True)
    return 1 if summary["FAIL"] else 0

if __name__ == "__main__":
    sys.exit(main())
