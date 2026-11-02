#!/usr/bin/env python3
"""Merge STCP robot evidence and enforce explicit test coverage gates.

Consumes JSON reports produced by stcp_test_robot.py and stcp_stress_robot.py.
Does not infer Zephyr/UDP coverage from Linux TCP results.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("reports", nargs="+", type=Path)
    p.add_argument("--output",type=Path,default=Path("/tmp/stcp-evidence-summary.json"))
    p.add_argument("--require-zephyr",action="store_true")
    p.add_argument("--require-udp",action="store_true")
    p.add_argument("--min-live-tcp",type=int,default=0)
    args=p.parse_args()
    if args.min_live_tcp<0: p.error("--min-live-tcp must be nonnegative")
    sources=[]; totals={"PASS":0,"FAIL":0,"SKIP":0}; live_tcp=0; zephyr_live=0; udp_live=0; problems=[]
    for path in args.reports:
        try:
            raw=path.read_bytes(); report=json.loads(raw)
            tests=report["tests"]
            if not isinstance(tests,list): raise ValueError("tests is not a list")
            seen={"PASS":0,"FAIL":0,"SKIP":0}
            for item in tests:
                status=item["status"]
                if status not in seen: raise ValueError("unknown status: "+str(status))
                seen[status]+=1
                name=str(item.get("name",""))
                group=str(item.get("group",""))
                category=str(item.get("category",""))
                if status=="PASS":
                    if name.startswith("linux-af-stcp-live-") or (group in ("sequential","parallel") and report.get("scope","").startswith("real Linux AF_STCP TCP")):
                        live_tcp+=1
                    if category=="external-live" and name.startswith("zephyr-external-live-"):
                        zephyr_live+=1
                    if category=="udp-live": udp_live+=1
            declared=report.get("summary",{})
            for key in ("PASS","FAIL"):
                if declared.get(key)!=seen[key]: raise ValueError(f"summary mismatch for {key}: declared {declared.get(key)}, observed {seen[key]}")
            if "SKIP" in declared and declared["SKIP"]!=seen["SKIP"]: raise ValueError("SKIP summary mismatch")
            for key in totals: totals[key]+=seen[key]
            sources.append({"path":str(path),"sha256":hashlib.sha256(raw).hexdigest(),"summary":seen,"scope":report.get("scope")})
        except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
            problems.append(f"{path}: {e}")
    gates={"no_failures":totals["FAIL"]==0 and not problems,
           "minimum_live_linux_tcp":live_tcp>=args.min_live_tcp,
           "zephyr_external_executed":not args.require_zephyr or zephyr_live>0,
           "udp_live_executed":not args.require_udp or udp_live>0}
    # External runner PASS is only proof that the runner returned 0; manual hardware evidence is still required.
    result={"schema_version":1,"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "totals":totals,"verified_test_counts":{"linux_tcp_live":live_tcp,"external_zephyr_runner":zephyr_live,"udp_live":udp_live},
            "gates":gates,"issues":problems,"sources":sources,
            "limitations":["Linux TCP loopback does not prove Zephyr or UDP interoperability.",
                           "An external Zephyr runner exit code alone does not prove a hardware test without its logs and device identity.",
                           "Model tests are not wire-level protocol fault injection."]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print("TOTALS",totals,"COVERAGE",result["verified_test_counts"])
    for name,passed in gates.items(): print(("PASS" if passed else "FAIL")+" GATE "+name)
    for issue in problems: print("ERROR",issue,file=sys.stderr)
    print("REPORT",args.output)
    return 0 if all(gates.values()) else 1
if __name__=="__main__": sys.exit(main())
