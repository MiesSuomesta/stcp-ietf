#!/usr/bin/env python3
"""Offline contract tests for the Zephyr hardware evidence orchestrator.

Synthetic fixtures test rejection/acceptance logic ONLY. They are not
interoperability evidence and never connect to hardware.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
ROBOT=ROOT/"tests/stcp_zephyr_interop_robot.py"
BASE={
    "transport":"tcp","linux_kernel":"test-kernel",
    "zephyr_firmware":"test-firmware","device_id":"test-board",
    "client_to_server_bytes":1024,"server_to_client_bytes":257,
    "client_to_server_verified":True,"server_to_client_verified":True,
    "handshake_completed":True,"authenticated_data_verified":True,
}
class InteropContractTests(unittest.TestCase):
    def run_fixture(self,modify=None,exit_code=0,transport="tcp"):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            payload=dict(BASE,transport=transport)
            if modify:modify(payload)
            fixture=directory/"fixture.json"
            fixture.write_text(json.dumps(payload))
            runner=directory/"runner.py"
            runner.write_text("#!/usr/bin/env python3\nimport pathlib,sys\na=sys.argv\np=pathlib.Path(a[a.index('--evidence')+1])\np.write_bytes(pathlib.Path("+repr(str(fixture))+").read_bytes())\nsys.exit("+str(exit_code)+")\n")
            runner.chmod(0o755)
            report=directory/"report.json"
            run=subprocess.run([sys.executable,str(ROBOT),"--runner",str(runner),
                                "--transport",transport,"--report",str(report)],
                               capture_output=True,text=True,timeout=15)
            return run.returncode,json.loads(report.read_text())
    def test_synthetic_valid_contract(self):
        code,report=self.run_fixture()
        self.assertEqual(code,0)
        self.assertEqual(report["summary"]["PASS"],1)
    def test_rejects_missing_required_field(self):
        code,report=self.run_fixture(lambda d:d.pop("handshake_completed"))
        self.assertNotEqual(code,0)
        self.assertEqual(report["summary"]["FAIL"],1)
    def test_rejects_false_handshake(self):
        code,_=self.run_fixture(lambda d:d.update(handshake_completed=False))
        self.assertNotEqual(code,0)
    def test_rejects_false_data_verification(self):
        code,_=self.run_fixture(lambda d:d.update(server_to_client_verified=False))
        self.assertNotEqual(code,0)
    def test_rejects_zero_bytes(self):
        code,_=self.run_fixture(lambda d:d.update(client_to_server_bytes=0))
        self.assertNotEqual(code,0)
    def test_rejects_boolean_byte_count(self):
        code,_=self.run_fixture(lambda d:d.update(client_to_server_bytes=True))
        self.assertNotEqual(code,0)
    def test_rejects_transport_mismatch(self):
        code,_=self.run_fixture(lambda d:d.update(transport="udp"))
        self.assertNotEqual(code,0)
    def test_rejects_runner_failure(self):
        code,_=self.run_fixture(exit_code=2)
        self.assertNotEqual(code,0)
    def test_rejects_empty_device_id(self):
        code,_=self.run_fixture(lambda d:d.update(device_id=" "))
        self.assertNotEqual(code,0)

if __name__=="__main__":unittest.main()
