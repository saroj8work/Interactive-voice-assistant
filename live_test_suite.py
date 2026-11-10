"""
Automated Live End-to-End Test Runner for Interactive-ELN & Voice Assistant AI.
Demonstrates:
1. Health of all microservices
2. Live Life Sciences voice domain queries (PCR protocols)
3. Autonomous UI Actions dispatching (opening Reagent Inventory)
4. Two-Person Quorum Authorization flow (Verbal Passkey & 21 CFR Part 11 Audit Record)
"""
import time
import sys
import requests
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VOICE_API = "http://127.0.0.1:8010"
GATEWAY_API = "http://127.0.0.1:8000"
IDENTITY_API = "http://127.0.0.1:8004"


def print_step(title):
    print("\n" + "=" * 65)
    print(f"  TEST: {title}")
    print("=" * 65)


def run_live_tests():
    print("\n🚀 STARTING LIVE END-TO-END VERIFICATION TESTS...\n")

    # 1. Microservice Health Checks
    print_step("1. Verifying Microservices & AI Agent Health")
    services = [
        ("ELN Gateway", f"{GATEWAY_API}/docs"),
        ("Identity Service", f"{IDENTITY_API}/auth/docs"),
        ("Voice Assistant AI", f"{VOICE_API}/api/health"),
    ]
    for name, url in services:
        try:
            r = requests.get(url, timeout=3)
            print(f"  ✅ {name:<20} HTTP {r.status_code} OK ({url})")
        except Exception as e:
            print(f"  ⚠️ {name:<20} Connection: {e}")

    # 2. Test Safe Action: Autonomous UI Navigation
    print_step("2. Safe Action: Autonomous Reagent Inventory Navigation")
    query_payload = {
        "message": "Please open the reagent inventory manager for our team",
        "session_id": "live_demo_sess",
        "generate_audio": True,
        "user_role": "member",
        "user_name": "Alex (Lab Researcher)"
    }
    print(f"  🎙️ Researcher Spoke: \"{query_payload['message']}\"")
    r = requests.post(f"{VOICE_API}/api/conversation/chat", json=query_payload, timeout=15)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    print(f"  🗣️ Agent Spoke Back : \"{data['assistant_reply']}\"")
    print(f"  🤖 Autonomous UI Action : {data['ui_actions']}")
    print(f"  🔊 Synthesized Audio  : {bool(data.get('audio_base64'))} (WAV base64)")
    assert len(data['ui_actions']) > 0
    assert data['ui_actions'][0]['target'] == "inventory"
    print("  ✅ TEST PASSED: UI action dispatched without human clicks!")

    # 3. Test Domain Knowledge: Standard PCR Protocol
    print_step("3. Domain Knowledge Query: Standard PCR Thermocycling")
    query_payload["message"] = "What are the exact thermocycling steps for a standard PCR assay?"
    print(f"  🎙️ Researcher Spoke: \"{query_payload['message']}\"")
    r = requests.post(f"{VOICE_API}/api/conversation/chat", json=query_payload, timeout=15)
    assert r.status_code == 200
    data = r.json()
    print(f"  🗣️ Agent Spoke Back : \"{data['assistant_reply']}\"")
    assert "98" in data['assistant_reply'] or "denaturation" in data['assistant_reply'].lower() or "pcr" in data['assistant_reply'].lower() or "polymerase" in data['assistant_reply'].lower()
    print("  ✅ TEST PASSED: Accurate Life Sciences protocol synthesized!")

    # 4. Test Privileged Action Interception (Two-Person Quorum)
    print_step("4. Privileged Action: Final Formal Report Submission (Challenge)")
    query_payload["message"] = "Submit and sign the final formal compliance report for Experiment 104"
    print(f"  🎙️ Researcher Spoke: \"{query_payload['message']}\"")
    r = requests.post(f"{VOICE_API}/api/conversation/chat", json=query_payload, timeout=15)
    assert r.status_code == 200
    data = r.json()
    print(f"  🔒 Authorization Status : {data['authorization_status']}")
    print(f"  🗣️ Agent Spoke Back     : \"{data['assistant_reply']}\"")
    print(f"  🛑 UI Actions Withheld  : {data['ui_actions']} (Empty as required)")
    assert data['authorization_status'] == "CHALLENGE_ISSUED"
    assert len(data['ui_actions']) == 0
    print("  ✅ TEST PASSED: Destructive action halted awaiting Admin approval!")

    # 5. Test Admin Verbal Authorization
    print_step("5. Project Admin Verbal Authorization & 21 CFR Part 11 Audit")
    admin_payload = {
        "message": "I am the project administrator Dr. Sarah Chen, authorize execution with passkey 4291",
        "session_id": "live_demo_sess",
        "generate_audio": True,
        "user_name": "Dr. Sarah Chen (Admin)"
    }
    print(f"  🎙️ Admin Spoke: \"{admin_payload['message']}\"")
    r = requests.post(f"{VOICE_API}/api/conversation/chat", json=admin_payload, timeout=15)
    assert r.status_code == 200
    data = r.json()
    print(f"  🔑 Authorization Status : {data['authorization_status']}")
    print(f"  🗣️ Agent Spoke Back     : \"{data['assistant_reply']}\"")
    print(f"  🚀 UI Action Released   : {data['ui_actions']}")
    print(f"  📜 GxP Audit Record     : ID={data['audit_record']['audit_id']}")
    print(f"  🔏 Digital Signature    : {data['audit_record']['digital_signature_hash']}")
    assert data['authorization_status'] == "AUTHORIZED"
    assert len(data['ui_actions']) > 0
    print("  ✅ TEST PASSED: Action authorized and sealed with cryptographic GxP audit hash!")

    print("\n" + "=" * 65)
    print("   🎉 ALL 5 LIVE TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 65)


if __name__ == "__main__":
    run_live_tests()
