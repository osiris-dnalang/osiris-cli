#!/usr/bin/env python3
"""
Test harness for OSIRIS IME Bridge Voice and Cloud DevOps Endpoints.
"""
import io
import json
from ime_interception_bridge import OsirisIMEBridgeServer

class MockRequest:
    def __init__(self, method: str, path: str, body: dict = None):
        self.method = method
        self.path = path
        self.headers = {}
        raw_body = json.dumps(body or {}).encode("utf-8") if body else b""
        self.headers["Content-Length"] = str(len(raw_body))
        self.rfile = io.BytesIO(raw_body)
        self.wfile = io.BytesIO()

def test_endpoints():
    print("[1] Testing do_GET /v1/cloud/hud...")
    server = OsirisIMEBridgeServer.__new__(OsirisIMEBridgeServer)
    server.rfile = io.BytesIO()
    server.wfile = io.BytesIO()
    server.path = "/v1/cloud/hud"
    server.headers = {}

    status_codes = []
    headers_sent = {}
    def mock_send_response(code):
        status_codes.append(code)
    def mock_send_header(k, v):
        headers_sent[k] = v
    def mock_end_headers():
        pass

    server.send_response = mock_send_response
    server.send_header = mock_send_header
    server.end_headers = mock_end_headers

    server.do_GET()
    hud_data = json.loads(server.wfile.getvalue().decode("utf-8"))
    assert hud_data["status"] == "OK"
    assert "branch" in hud_data
    assert "head_sha" in hud_data
    print(f"    ✓ HUD OK: Branch={hud_data['branch']}, SHA={hud_data['head_sha']}")

    print("[2] Testing do_POST /v1/cloud/dispatch...")
    server.wfile = io.BytesIO()
    payload = {"action": "TRIGGER_GITHUB_WORKFLOW", "workflow": "CI Test Suite"}
    raw_payload = json.dumps(payload).encode("utf-8")
    server.rfile = io.BytesIO(raw_payload)
    server.headers = {"Content-Length": str(len(raw_payload))}
    server.path = "/v1/cloud/dispatch"
    server.do_POST()
    dispatch_data = json.loads(server.wfile.getvalue().decode("utf-8"))
    assert dispatch_data["status"] == "DISPATCHED"
    assert "SYS-021 Grant Verified" in dispatch_data["receipt"]
    print(f"    ✓ Dispatch OK: {dispatch_data['receipt']}")

    print("[3] Testing do_POST /v1/voice/interact...")
    server.wfile = io.BytesIO()
    voice_payload = {
        "transcript": "synthesize quantum circuit and verify evidence gate",
        "host_package": "com.example.osiris",
        "client": "OSIRIS_VOICE_TEST"
    }
    raw_v = json.dumps(voice_payload).encode("utf-8")
    server.rfile = io.BytesIO(raw_v)
    server.headers = {"Content-Length": str(len(raw_v))}
    server.path = "/v1/voice/interact"
    server.do_POST()
    voice_data = json.loads(server.wfile.getvalue().decode("utf-8"))
    assert voice_data["status"] == "PROCESSED"
    assert "spoken_response" in voice_data
    assert "gap_disposition" in voice_data
    print(f"    ✓ Voice OK: Disposition={voice_data['gap_disposition']}, Spoken={voice_data['spoken_response'][:50]}...")

    print("\nALL BRIDGE ENDPOINT TESTS PASSED DETERMINISTICALLY.")

if __name__ == "__main__":
    test_endpoints()
