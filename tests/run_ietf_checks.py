#!/usr/bin/env python3
"""Run STCP IETF offline checks and write a reproducible JSON report.

Run from any directory: python3 tests/run_ietf_checks.py
Requires: python3 -m pip install 'cryptography>=46,<50' 'xml2rfc>=3,<4'
No STCP kernel module, network connection, or Zephyr device is needed.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "internet-draft" / "draft-paxsudos-stcp-00.xml"

def run(name, command, cwd=ROOT):
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True,
                                text=True, errors="replace", timeout=180)
        status = "PASS" if result.returncode == 0 else "FAIL"
        return dict(name=name, status=status, command=command,
                    exit_code=result.returncode,
                    duration_seconds=round(time.monotonic() - started, 3),
                    stdout=result.stdout[-30000:], stderr=result.stderr[-30000:])
    except FileNotFoundError as exc:
        return dict(name=name, status="SKIP", command=command,
                    reason=str(exc))
    except subprocess.TimeoutExpired:
        return dict(name=name, status="FAIL", command=command,
                    reason="Timed out after 180 seconds")

def check_xml():
    started = time.monotonic()
    try:
        root = ET.parse(DRAFT).getroot()
        assert root.tag == "rfc" and root.get("version") == "3", "Expected RFCXML v3"
        # A nested section must not be followed by a paragraph in its parent.
        for section in root.iter("section"):
            seen_subsection = False
            for child in section:
                if child.tag == "section":
                    seen_subsection = True
                elif seen_subsection and child.tag in ("t", "ol", "ul", "dl"):
                    raise ValueError("Content follows subsection in " + section.get("anchor", "?"))
        return dict(name="RFCXML structure", status="PASS",
                    duration_seconds=round(time.monotonic()-started, 3))
    except (ET.ParseError, AssertionError, ValueError) as exc:
        return dict(name="RFCXML structure", status="FAIL", reason=str(exc),
                    duration_seconds=round(time.monotonic()-started, 3))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "tests" / "ietf-check-report.json")
    parser.add_argument("--no-render", action="store_true", help="Skip xml2rfc rendering")
    args = parser.parse_args()
    results = [run("Crypto vectors", [sys.executable, "-m", "unittest", "discover",
                                      "-s", "tests", "-p", "test_stcp_vectors.py", "-v"]),
               check_xml()]
    if not args.no_render:
        with tempfile.TemporaryDirectory(prefix="stcp-ietf-") as temp:
            results.append(run("RFCXML rendering", ["xml2rfc", "--text", "--out",
                           str(Path(temp) / "draft.txt"), str(DRAFT)]))
    report = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "git_commit": None,
        "scope": "Offline reference tests only; not Linux/Zephyr interoperability evidence",
        "checks": results,
    }
    git = run("git revision", ["git", "rev-parse", "HEAD"])
    if git["status"] == "PASS":
        report["git_commit"] = git["stdout"].strip()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for result in results:
        print(f'{result["status"]:4} {result["name"]}')
        if result["status"] != "PASS":
            print("    " + result.get("reason", result.get("stderr", "").strip()[-300:]))
    print("Report:", args.report)
    return 1 if any(x["status"] == "FAIL" for x in results) else (2 if any(x["status"] == "SKIP" for x in results) else 0)

if __name__ == "__main__":
    sys.exit(main())
