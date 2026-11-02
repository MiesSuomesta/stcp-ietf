#!/usr/bin/env python3
"""Live AF_STCP TCP payload-size and immediate-DATA matrix.

This is an actual kernel-socket test, NOT crafted handshake injection, UDP,
Zephyr interoperability, or fuzzing. No kernel/SDK modifications.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import os

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_SIZES=(1,16,17,18,40,64,255,256,257,1024,1400,1500,3000,4096,12000,16384,65536)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sizes",default=",".join(map(str,DEFAULT_SIZES)))
    p.add_argument("--repeat",type=int,default=5)
    p.add_argument("--port",type=int,default=19600)
    p.add_argument("--timeout",type=int,default=45)
    p.add_argument("--report",type=Path,default=Path("/tmp/stcp-payload-report.json"))
    a=p.parse_args()
    try: sizes=[int(s) for s in a.sizes.split(",")]
    except ValueError: p.error("sizes must be comma-separated integers")
    if not sizes or any(n<1 or n>1048576 for n in sizes) or a.repeat<1 or a.timeout<1 or not 1024<=a.port<=65535:
        p.error("invalid sizes, repeat, timeout or port")
    results=[]
    with tempfile.TemporaryDirectory(prefix="stcp-payload-") as d:
        exe=Path(d)/"payload"
        build=subprocess.run(["gcc","-O2","-Wall","-Wextra","-pthread","-o",str(exe),str(ROOT/"tests/stcp_tcp_payload_boundaries.c")],capture_output=True,text=True)
        if build.returncode:
            print(build.stderr,file=sys.stderr)
            return 1
        print("[PASS] payload harness build",flush=True)
        stop=False
        for n in sizes:
            for iteration in range(1,a.repeat+1):
                start=time.monotonic()
                try:
                    r=subprocess.run([str(exe),str(a.port),str(n)],capture_output=True,text=True,timeout=a.timeout)
                    status="PASS" if r.returncode==0 else "FAIL"
                    output=(r.stdout+r.stderr)[-4000:]
                except (subprocess.TimeoutExpired,OSError) as e:
                    status="FAIL"; output=str(e)
                item=dict(name=f"linux-tcp-immediate-data-{n}B-{iteration:03d}",category="live",status=status,
                          size_bytes=n,iteration=iteration,duration_seconds=round(time.monotonic()-start,4),details=output)
                results.append(item)
                if status=="FAIL":
                    print(f"[FAIL] size={n} iteration={iteration}: {output}",flush=True)
                    stop=True; break
            if stop: break
            print(f"[PASS] size={n} bytes, repeats={a.repeat}",flush=True)
    counts={s:sum(t["status"]==s for t in results) for s in ("PASS","FAIL","SKIP")}
    report=dict(schema_version=1,timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                scope="real Linux AF_STCP TCP immediate-DATA and bidirectional payload integrity only",
                host_kernel=os.uname().release,parameters=dict(sizes=sizes,repeat=a.repeat,port=a.port,timeout=a.timeout),
                summary=counts,tests=results,
                limitations=["No Zephyr or UDP test","No crafted wire-level handshake injection","Sizes are application payload lengths, not wire frame lengths"])
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print("SUMMARY",counts,"REPORT",a.report,flush=True)
    return int(counts["FAIL"]>0)
if __name__=="__main__":sys.exit(main())
