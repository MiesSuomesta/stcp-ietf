#!/usr/bin/env python3
"""AF_STCP TCP stress robot. Real kernel sockets; no production source changes.

Runs the repository's existing verified C loopback binary in sequential and
parallel waves. Does NOT claim UDP, crafted handshake, or Zephyr coverage.
"""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
import tempfile
import time
import os
import sys
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
def run_case(exe, port, timeout):
    started = time.monotonic()
    try:
        r = subprocess.run([str(exe), str(port)], capture_output=True, text=True, timeout=timeout)
        return dict(port=port, status="PASS" if r.returncode == 0 else "FAIL", returncode=r.returncode,
                    seconds=round(time.monotonic()-started, 4), output=(r.stdout+r.stderr)[-2000:])
    except subprocess.TimeoutExpired as e:
        return dict(port=port, status="FAIL", returncode=None,
                    seconds=round(time.monotonic()-started, 4), output=f"timeout after {timeout}s: {e}")
    except OSError as e:
        return dict(port=port, status="FAIL", returncode=None,
                    seconds=round(time.monotonic()-started, 4), output=str(e))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sequential", type=int, default=200)
    p.add_argument("--parallel", type=int, default=10)
    p.add_argument("--waves", type=int, default=10)
    p.add_argument("--base-port", type=int, default=19533)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--report", type=Path, default=Path("/tmp/stcp-stress-report.json"))
    args = p.parse_args()
    if min(args.sequential, args.parallel, args.waves, args.timeout) < 1 or args.base_port < 1024 or args.base_port + args.parallel >= 65536 or args.parallel > 128:
        p.error("invalid counts or port range")
    results=[]
    with tempfile.TemporaryDirectory(prefix="stcp-stress-") as temp:
        exe = Path(temp)/"loopback"
        build = subprocess.run(["gcc","-O2","-Wall","-Wextra","-pthread","-o",str(exe),str(ROOT/"tests/stcp_kernel_loopback.c")],capture_output=True,text=True)
        if build.returncode:
            print(build.stderr,file=sys.stderr)
            return 1
        print("[PASS] build",flush=True)
        for i in range(args.sequential):
            item=run_case(exe,args.base_port,args.timeout)
            item.update(group="sequential", iteration=i+1)
            results.append(item)
            if (i+1)%25==0 or item["status"]=="FAIL":
                print(f"[{item['status']}] sequential {i+1}/{args.sequential}",flush=True)
            if item["status"]=="FAIL": break
        if not any(x["status"]=="FAIL" for x in results):
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
                for wave in range(args.waves):
                    batch=list(pool.map(lambda port:run_case(exe,port,args.timeout),
                                        range(args.base_port,args.base_port+args.parallel)))
                    for item in batch: item.update(group="parallel",wave=wave+1)
                    results.extend(batch)
                    failed=sum(x["status"]=="FAIL" for x in batch)
                    print(f"[{'FAIL' if failed else 'PASS'}] parallel wave {wave+1}/{args.waves}, clients={args.parallel}, failed={failed}",flush=True)
                    if failed: break
    counts={k:sum(x["status"]==k for x in results) for k in ("PASS","FAIL")}
    report=dict(schema_version=1,timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                scope="real Linux AF_STCP TCP bidirectional loopback only; no Zephyr, UDP or crafted frames",
                kernel=os.uname().release,parameters=vars(args)|{"report":str(args.report)},
                summary=counts,tests=results)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
    print("SUMMARY",counts,"REPORT",args.report,flush=True)
    return 1 if counts["FAIL"] else 0

if __name__=="__main__":
    sys.exit(main())
