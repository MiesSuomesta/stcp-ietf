#!/usr/bin/env python3
"""Linux AF_STCP TCP lifecycle regression runner; no kernel/SDK changes.

Exercises fresh-socket reconnection, request/reply integrity and local close.
Does not claim forced disconnect, malformed wire, UDP or Zephyr coverage.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--connections",type=int,default=100)
    p.add_argument("--repeat",type=int,default=5)
    p.add_argument("--port",type=int,default=19650)
    p.add_argument("--timeout",type=int,default=120)
    p.add_argument("--report",type=Path,default=Path("/tmp/stcp-lifecycle-report.json"))
    a=p.parse_args()
    if not 1<=a.connections<=10000 or a.repeat<1 or not 1024<=a.port<=65535 or a.timeout<1:
        p.error("invalid parameters")
    results=[]
    with tempfile.TemporaryDirectory(prefix="stcp-lifecycle-") as d:
        exe=Path(d)/"lifecycle"
        b=subprocess.run(["gcc","-O2","-Wall","-Wextra","-pthread","-o",str(exe),str(ROOT/"tests/stcp_tcp_lifecycle.c")],capture_output=True,text=True)
        if b.returncode:
            print(b.stderr,file=sys.stderr);return 1
        print("[PASS] lifecycle harness build",flush=True)
        for i in range(1,a.repeat+1):
            start=time.monotonic()
            try:
                r=subprocess.run([str(exe),str(a.port),str(a.connections)],capture_output=True,text=True,timeout=a.timeout)
                status="PASS" if r.returncode==0 else "FAIL"
                details=f"exit={r.returncode}\n"+r.stdout+r.stderr
            except (OSError,subprocess.TimeoutExpired) as e:
                status="FAIL";details=str(e)
            results.append(dict(name=f"linux-tcp-lifecycle-{i:03d}",category="live",status=status,
                                connections=a.connections,duration_seconds=round(time.monotonic()-start,3),details=details[-4000:]))
            print(f"[{status}] lifecycle batch {i}/{a.repeat} ({a.connections} connections)",flush=True)
            if status=="FAIL":print(details[-3000:],file=sys.stderr);break
    summary={s:sum(t["status"]==s for t in results) for s in ("PASS","FAIL","SKIP")}
    report=dict(schema_version=1,timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                scope="real Linux AF_STCP TCP fresh-socket lifecycle with sequential connections, reply integrity and close",
                host_kernel=os.uname().release,parameters=dict(connections=a.connections,repeat=a.repeat,port=a.port,timeout=a.timeout),
                summary=summary,successful_connections=summary["PASS"]*a.connections,tests=results,
                limitations=["No forced network failure or EOF verification","No UDP, Zephyr, crafted handshake or fuzzing","A timeout may indicate a hang; inspect kernel logs and process state"])
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print("SUMMARY",summary,"SUCCESSFUL_CONNECTIONS",report["successful_connections"],"REPORT",a.report,flush=True)
    return 1 if summary["FAIL"] else 0
if __name__=="__main__":sys.exit(main())
