#!/usr/bin/env python3
"""Run operator-provided Linux/Zephyr hardware interoperability checks.

This is an orchestration adapter, NOT a Zephyr implementation. The operator's
runner must produce a machine-readable JSON result for each real transport.
Missing runner, missing evidence or unsupported transport cannot PASS.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runner",type=Path,required=True,help="executable hardware test adapter")
    p.add_argument("--transport",choices=("tcp","udp","both"),default="both")
    p.add_argument("--timeout",type=int,default=120)
    p.add_argument("--repeat",type=int,default=1)
    p.add_argument("--report",type=Path,default=Path("/tmp/stcp-zephyr-interop.json"))
    a=p.parse_args()
    if a.timeout<1 or a.repeat<1:p.error("timeout/repeat must be positive")
    if not a.runner.is_file() or not os.access(a.runner,os.X_OK):
        p.error("runner must exist and be executable")
    tests=[]
    with tempfile.TemporaryDirectory(prefix="stcp-zephyr-evidence-") as d:
        for transport in (("tcp","udp") if a.transport=="both" else (a.transport,)):
            for iteration in range(1,a.repeat+1):
                path=Path(d)/f"{transport}-{iteration}.json"
                start=time.monotonic()
                try:
                    run=subprocess.run([str(a.runner.resolve()),"--transport",transport,"--evidence",str(path)],
                        capture_output=True,text=True,timeout=a.timeout)
                    raw=path.read_bytes()
                    evidence=json.loads(raw)
                    required=("transport","linux_kernel","zephyr_firmware","device_id",
                              "client_to_server_bytes","server_to_client_bytes",
                              "client_to_server_verified","server_to_client_verified",
                              "handshake_completed","authenticated_data_verified")
                    missing=[k for k in required if k not in evidence]
                    if missing:raise ValueError("missing fields: "+", ".join(missing))
                    if evidence["transport"]!=transport:raise ValueError("transport mismatch")
                    for k in ("linux_kernel","zephyr_firmware","device_id"):
                        if not isinstance(evidence[k],str) or not evidence[k].strip():
                            raise ValueError("empty or invalid "+k)
                    for k in ("client_to_server_bytes","server_to_client_bytes"):
                        if type(evidence[k]) is not int or evidence[k]<=0:raise ValueError("invalid "+k)
                    for k in ("client_to_server_verified","server_to_client_verified",
                              "handshake_completed","authenticated_data_verified"):
                        if evidence[k] is not True:raise ValueError("not verified: "+k)
                    if run.returncode:raise ValueError(f"runner exit {run.returncode}")
                    status="PASS";reason="operator hardware evidence verified"
                    digest=hashlib.sha256(raw).hexdigest()
                except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.TimeoutExpired) as exc:
                    status="FAIL";reason=str(exc);digest=None
                tests.append(dict(name=f"zephyr-{transport}-{iteration:03d}",status=status,
                    duration_seconds=round(time.monotonic()-start,3),
                    reason=reason,evidence_sha256=digest))
                print(f"[{status}] {transport} iteration={iteration}: {reason}",flush=True)
                if status=="FAIL":break
            if tests[-1]["status"]=="FAIL":break
    summary={s:sum(t["status"]==s for t in tests) for s in ("PASS","FAIL","SKIP")}
    report=dict(schema_version=1,timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        scope="operator-provided real Linux-Zephyr hardware interoperability evidence",
        runner=str(a.runner.resolve()),transport=a.transport,summary=summary,tests=tests,
        limitations=["The adapter validates declared evidence; it cannot independently attest that the runner used physical Zephyr hardware.",
                     "Operator runner must independently verify handshake, authenticated data and bidirectional payload bytes."])
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print("SUMMARY",summary,"REPORT",a.report)
    return 1 if summary["FAIL"] else 0
if __name__=="__main__":sys.exit(main())
