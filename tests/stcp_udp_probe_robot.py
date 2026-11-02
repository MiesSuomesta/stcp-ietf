#!/usr/bin/env python3
"""Experimental live AF_STCP UDP smoke runner.

Compiles a standalone C probe, runs it under a hard timeout, saves evidence.
No kernel or SDK modification. FAIL means the attempted socket API path failed,
not necessarily that STCP UDP as a protocol is broken.
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
    p.add_argument("--port",type=int,default=19700)
    p.add_argument("--repeat",type=int,default=1)
    p.add_argument("--timeout",type=int,default=20)
    p.add_argument("--report",type=Path,default=Path("/tmp/stcp-udp-probe.json"))
    a=p.parse_args()
    if not 1024<=a.port<=65535 or a.repeat<1 or a.timeout<1:p.error("invalid arguments")
    tests=[]
    with tempfile.TemporaryDirectory(prefix="stcp-udp-") as d:
        exe=Path(d)/"udp-probe"
        build=subprocess.run(["gcc","-O2","-Wall","-Wextra","-pthread","-o",str(exe),str(ROOT/"tests/stcp_udp_probe.c")],capture_output=True,text=True)
        if build.returncode:
            tests.append(dict(name="udp-probe-build",status="FAIL",details=build.stderr))
        else:
            tests.append(dict(name="udp-probe-build",status="PASS",details=build.stderr))
            for i in range(1,a.repeat+1):
                started=time.monotonic()
                try:
                    run=subprocess.run([str(exe),str(a.port)],capture_output=True,text=True,timeout=a.timeout)
                    status="PASS" if run.returncode==0 else "FAIL"
                    details=f"exit={run.returncode}\n{run.stdout}{run.stderr}"
                except (OSError,subprocess.TimeoutExpired) as e:
                    status="FAIL";details=str(e)
                tests.append(dict(name=f"udp-probe-{i:03d}",status=status,
                                  seconds=round(time.monotonic()-started,3),details=details[-6000:]))
                print(f"[{status}] UDP probe {i}/{a.repeat}: {details[-500:]}",flush=True)
                if status=="FAIL":break
    summary={s:sum(x["status"]==s for x in tests) for s in ("PASS","FAIL","SKIP")}
    result=dict(schema_version=1,timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                scope="experimental AF_STCP protocol 254 UDP bind/listen/accept and bidirectional 32-byte smoke test",
                host_kernel=os.uname().release,parameters=dict(port=a.port,repeat=a.repeat,timeout=a.timeout),
                summary=summary,tests=tests,
                limitations=["The chosen UDP socket API may be unsupported even when other UDP paths work.",
                             "No Zephyr hardware, UDP retransmission, fragmentation or loss injection tested."])
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2)+"\n")
    print("SUMMARY",summary,"REPORT",a.report,flush=True)
    return 1 if summary["FAIL"] else 0
if __name__=="__main__":sys.exit(main())
