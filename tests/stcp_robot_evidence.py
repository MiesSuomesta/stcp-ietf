#!/usr/bin/env python3
"""Verify STCP IETF parent/child robot evidence and emit an auditable summary.

Only counts evidence present in JSON. Never equates model checks with live
interoperability, or claims Zephyr coverage when the runner was skipped.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

STATUSES=("PASS","FAIL","SKIP")
EXPECTED=("tcp-stress","tcp-payload","tcp-lifecycle","udp-smoke","udp-matrix")
def read(path):
    data=path.read_bytes()
    return json.loads(data),hashlib.sha256(data).hexdigest()
def count(tests):
    if not isinstance(tests,list):raise ValueError("tests must be a list")
    totals={k:0 for k in STATUSES}
    for item in tests:
        status=item["status"]
        if status not in totals:raise ValueError("unknown status "+str(status))
        totals[status]+=1
    return totals
def verify_report(data,kind):
    declared=data["summary"]
    observed=count(data["tests"])
    for key in STATUSES:
        value=declared.get(key,0)
        if type(value) is not int or value<0 or value!=observed[key]:
            raise ValueError(f"{kind} {key}: declared={value}, observed={observed[key]}")
    return observed
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("parent",type=Path)
    p.add_argument("--output",type=Path,default=Path("/tmp/stcp-robot-evidence-summary.json"))
    p.add_argument("--require-live-suite",action="store_true")
    p.add_argument("--require-zephyr",action="store_true")
    args=p.parse_args()
    issues=[];suites=[];parent_summary=None;parent_hash=None
    child_total={k:0 for k in STATUSES}
    tcp_connections=0;udp_messages=0
    try:
        parent,parent_hash=read(args.parent)
        parent_summary=verify_report(parent,"parent")
        declared_suites=parent.get("child_suites",[])
        if not isinstance(declared_suites,list):raise ValueError("child_suites must be a list")
        names=[s["name"] for s in declared_suites]
        if len(names)!=len(set(names)):issues.append("duplicate child suite names")
        if args.require_live_suite and set(names)!=set(EXPECTED):
            issues.append("missing required live suites: "+str(sorted(set(EXPECTED)-set(names))))
        for suite in declared_suites:
            name=suite["name"]
            path=Path(suite["report"])
            # Parent-generated suite reports must be located in the adjacent suite directory.
            allowed=(args.parent.parent/(args.parent.stem+"-suites")).resolve()
            if path.resolve().parent!=allowed:
                issues.append(f"{name}: report outside expected suite directory")
                continue
            try:
                child,digest=read(path)
                observed=verify_report(child,name)
                if suite.get("summary")!=child["summary"]:
                    issues.append(f"{name}: parent and child summaries differ")
                if suite.get("status")!=("PASS" if observed["FAIL"]==0 and observed["PASS"]>0 else "FAIL"):
                    issues.append(f"{name}: parent suite status differs from child")
                for k in STATUSES:child_total[k]+=observed[k]
                if name=="tcp-stress":tcp_connections+=observed["PASS"]
                if name=="tcp-lifecycle":
                    claimed=child.get("successful_connections")
                    expected=observed["PASS"]*child.get("parameters",{}).get("connections",0)
                    if type(claimed) is not int or claimed!=expected:
                        issues.append("tcp-lifecycle successful_connections inconsistent")
                    else:tcp_connections+=claimed
                if name=="tcp-payload":tcp_connections+=observed["PASS"]
                if name=="udp-matrix":
                    actual=sum(len(t.get("sizes",[])) for t in child["tests"] if t["status"]=="PASS")
                    if child.get("verified_messages")!=actual:issues.append("udp-matrix verified_messages inconsistent")
                    udp_messages+=actual
                if name=="udp-smoke":
                    udp_messages+=sum(t["status"]=="PASS" and t["name"].startswith("udp-probe-") for t in child["tests"])
                suites.append(dict(name=name,summary=observed,sha256=digest,report=str(path)))
            except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
                issues.append(f"{name}: {exc}")
        # Confirm each recorded suite PASS in parent corresponds to a child.
        parent_suites={t["name"]:t["status"] for t in parent["tests"] if t["name"].startswith("suite-")}
        for suite in declared_suites:
            if parent_suites.get("suite-"+suite["name"])!=suite["status"]:
                issues.append("parent test entry differs for "+suite["name"])
        if args.require_zephyr and not any(t["name"].startswith("zephyr-external-live-") and t["status"]=="PASS" for t in parent["tests"]):
            issues.append("no successful external Zephyr test recorded")
        if parent_summary["FAIL"]:issues.append("parent has failing tests")
        if child_total["FAIL"]:issues.append("child suites have failing tests")
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        issues.append(f"parent: {exc}")
    result=dict(schema_version=1,parent=str(args.parent),parent_sha256=parent_hash,
                parent_summary=parent_summary,child_summary=child_total,
                verified_tcp_connection_cases=tcp_connections,
                verified_udp_message_exchanges=udp_messages,
                child_suites=suites,issues=issues,passed=not issues,
                limitations=["TCP connection cases may be separate from parent loopback tests.",
                             "UDP exchange count reflects tested send/echo pairs, not packet-loss robustness.",
                             "No Zephyr interoperability is claimed without external live evidence.",
                             "A passing test is not a security certification."])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print("EVIDENCE", "PASS" if not issues else "FAIL", "parent",parent_summary,"children",child_total)
    print("TCP_CASES",tcp_connections,"UDP_EXCHANGES",udp_messages)
    for issue in issues:print("ISSUE",issue,file=sys.stderr)
    print("REPORT",args.output)
    return 1 if issues else 0
if __name__=="__main__":sys.exit(main())
