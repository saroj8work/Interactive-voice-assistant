import urllib.request
import json

# Check identity service health and test login
try:
    req = urllib.request.Request("http://127.0.0.1:8004/health")
    with urllib.request.urlopen(req, timeout=3) as resp:
        print("Identity Service Health:", resp.read().decode())
except Exception as e:
    print("Health check failed:", e)

# Test login attempts
test_creds = [
    ("default", "admin@interactive-eln.local", "Admin123!"),
    ("default", "researcher@interactive-eln.local", "Researcher123!"),
    ("aura-lab", "admin@aura-lab.local", "Admin123!"),
    ("demo", "demo@interactive-eln.local", "Demo123!"),
]

for org, email, pw in test_creds:
    payload = json.dumps({"organization_slug": org, "email": email, "password": pw}).encode()
    req = urllib.request.Request("http://127.0.0.1:8004/auth/login", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"Login SUCCESS for {org} / {email}:", resp.status)
    except urllib.error.HTTPError as e:
        print(f"Login {e.code} for {org} / {email}:", e.read().decode()[:80])
    except Exception as e:
        print(f"Login error for {org} / {email}:", e)

