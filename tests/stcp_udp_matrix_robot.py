#!/usr/bin/env python3
"""Bounded real AF_STCP UDP message integrity, reconnect and concurrency robot.

Each C process uses one client/server pair and verifies individual recv lengths.
Different processes use distinct ports. No kernel/SDK changes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_SIZES=(1,16,17,18,40,64,255,256,257,1024,1400,1500,3000,4096,12000,16384,65536)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sizes",default=",".join(map(str,DEFAULT_SIZES)))
    p.add_argument("--repeat",type=int,default=3)
    p.add_argument("--parallel",type=int,default=4)
    p.add_argument("--waves",type=int,default=3)
    p.add_argument("--base-port",type=int,default=19720)
    p.add_argument("--timeout",type=int,default=45)
    p.add_argument("--report",type=Path,default=Path("/tmp/stcp-udp-matrix.json"))
    a=p.parse_args()
    try:sizes=[int(s) for s in a.sizes.split(",")]
    except ValueError:p.error("sizes must be integers")
    if not sizes or len(sizes)>128 or any(n<1 or n>65536 for n in sizes) or min(a.repeat,a.parallel,a.waves,a.timeout)<1 or a.parallel>32 or not 1024<=a.base_port<=65535-a.parallel:
        p.error("invalid sizes, counts, port or timeout")
    tests=[]
    with tempfile.TemporaryDirectory(prefix="stcp-udp-matrix-") as tmp:
        exe=Path(tmp)/"udp-messages"
        build=subprocess.run(["gcc","-O2","-Wall","-Wextra","-pthread","-o",str(exe),str(ROOT/"tests/stcp_udp_messages.c")],capture_output=True,text=True)
        if build.returncode:
            print(build.stderr,file=sys.stderr);return 1
        print("[PASS] UDP message harness build",flush=True)
        def run(name,port,sequence):
            started=time.monotonic()
            try:
                r=subprocess.run([str(exe),str(port),*map(str,sequence)],capture_output=True,text=True,timeout=a.timeout)
                status="PASS" if r.returncode==0 else "FAIL"
                details=f"exit={r.returncode}\n"+r.stdout+r.stderr
            except (OSError,subprocess.TimeoutExpired) as e:
                status="FAIL";details=str(e)
            return dict(name=name,category="udp-live",status=status,port=port,sizes=sequence,
                        duration_seconds=round(time.monotonic()-started,3),details=details[-4000:])
        # Sequential cases: isolated messages, then alternating message sizes on a single connection.
        cases=[[n] for n in sizes]+[sizes,list(reversed(sizes))]
        failed=False
        for repetition in range(a.repeat):
            for index,sequence in enumerate(cases):
                item=run(f"udp-sequential-{repetition+1:03d}-{index+1:03d}",a.base_port,sequence)
                tests.append(item)
                if item["status"]=="FAIL":
                    print("[FAIL]",item["name"],item["details"],flush=True);failed=True;break
            if failed:break
            print(f"[PASS] UDP sequential pass {repetition+1}/{a.repeat} cases={len(cases)}",flush=True)
        # Distinct ports, concurrent independent client/server pairs.
        if not failed:
            with ThreadPoolExecutor(max_workers=a.parallel) as pool:
                for wave in range(a.waves):
                    futures=[pool.submit(run,f"udp-parallel-wave-{wave+1:03d}-client-{j+1:03d}",a.base_port+j,sizes)
                             for j in range(a.parallel)]
                    for f in as_completed(futures):
                        item=f.result();tests.append(item)
                        if item["status"]=="FAIL":
                            print("[FAIL]",item["name"],item["details"],flush=True);failed=True
                    if failed:break
                    print(f"[PASS] UDP parallel wave {wave+1}/{a.waves} clients={a.parallel}",flush=True)
    summary={s:sum(t["status"]==s for t in tests) for s in ("PASS","FAIL","SKIP")}
    report=dict(schema_version=1,timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                scope="real Linux AF_STCP UDP message-length and payload-integrity test, sequential fresh sockets and independent parallel socket pairs",
                host_kernel=os.uname().release,parameters=dict(sizes=sizes,repeat=a.repeat,parallel=a.parallel,waves=a.waves,base_port=a.base_port,timeout=a.timeout),
                summary=summary,verified_messages=sum(len(t["sizes"]) for t in tests if t["status"]=="PASS"),
                tests=tests,limitations=["One outstanding message at a time: no back-to-back datagram queue stress",
                                         "Parallel tests use independent server ports, not a shared UDP listener",
                                         "No packet loss, reordering, forced disconnect, Zephyr, or malformed-wire injection"])
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print("SUMMARY",summary,"VERIFIED_MESSAGES",report["verified_messages"],"REPORT",a.report,flush=True)
    return int(summary["FAIL"]>0)
if __name__=="__main__":sys.exit(main())
