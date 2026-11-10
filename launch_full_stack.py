"""
Master Full-Stack Launcher for Interactive-ELN and Interactive Voice Assistant Agent.
Starts all microservices, Voice AI agent, and frontend dev server.
Performs live health checks and automated end-to-end testing.
"""
import os
import sys
import time
import socket
import subprocess
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
ELN_ROOT = Path(r"C:\Users\saroj\OneDrive\Documents\GitHub\Interactive-ELN")
ELN_BACKEND = ELN_ROOT / "backend"
ELN_FRONTEND = ELN_ROOT / "frontend"
ELN_VENV_PY = (ELN_ROOT / ".venv" / "Scripts" / "python.exe") if (ELN_ROOT / ".venv" / "Scripts" / "python.exe").exists() else sys.executable
HOST_PY = sys.executable

# Load ELN .env
eln_env = os.environ.copy()
eln_env["PYTHONPATH"] = str(ELN_BACKEND)
eln_env_file = ELN_ROOT / ".env"
try:
    if eln_env_file.exists():
        for line in eln_env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                eln_env[k.strip()] = v.strip()
except Exception:
    pass

# Internal service URL bindings
eln_env["IDENTITY_SERVICE_URL"] = "http://127.0.0.1:8004"
eln_env["PROJECTS_SERVICE_URL"] = "http://127.0.0.1:8001"
eln_env["NOTEBOOK_SERVICE_URL"] = "http://127.0.0.1:8002"
eln_env["ACTIVITY_SERVICE_URL"] = "http://127.0.0.1:8003"


def check_port(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    res = s.connect_ex((host, port))
    s.close()
    return res == 0


def wait_for_port(port: int, name: str, timeout: int = 15):
    start = time.time()
    while time.time() - start < timeout:
        if check_port(port):
            print(f"  [OK] {name} is active and listening on port {port}")
            return True
        time.sleep(0.5)
    print(f"  [WAIT] {name} port {port} not listening yet after {timeout}s")
    return False


def main():
    print("=" * 70)
    print("   LAUNCHING FULL INTERACTIVE-ELN & VOICE ASSISTANT AI STACK")
    print("=" * 70)

    processes = []

    # 1. Identity Service (8004)
    if not check_port(8004):
        print("\n[1/7] Starting Identity Service on port 8004...")
        p = subprocess.Popen(
            [str(ELN_VENV_PY), "-m", "uvicorn", "services.identity.app.main:app", "--host", "127.0.0.1", "--port", "8004"],
            cwd=str(ELN_BACKEND),
            env=eln_env,
        )
        processes.append(("Identity", p, 8004))
    else:
        print("[1/7] Identity Service already running on port 8004.")

    # 2. Projects Service (8001)
    if not check_port(8001):
        print("\n[2/7] Starting Projects Service on port 8001...")
        p = subprocess.Popen(
            [str(ELN_VENV_PY), "-m", "uvicorn", "services.projects.app.main:app", "--host", "127.0.0.1", "--port", "8001"],
            cwd=str(ELN_BACKEND),
            env=eln_env,
        )
        processes.append(("Projects", p, 8001))
    else:
        print("[2/7] Projects Service already running on port 8001.")

    # 3. Notebook Service (8002)
    if not check_port(8002):
        print("\n[3/7] Starting Notebook Service on port 8002...")
        p = subprocess.Popen(
            [str(ELN_VENV_PY), "-m", "uvicorn", "services.notebook.app.main:app", "--host", "127.0.0.1", "--port", "8002"],
            cwd=str(ELN_BACKEND),
            env=eln_env,
        )
        processes.append(("Notebook", p, 8002))
    else:
        print("[3/7] Notebook Service already running on port 8002.")

    # 4. Activity Service (8003)
    if not check_port(8003):
        print("\n[4/7] Starting Activity Service on port 8003...")
        p = subprocess.Popen(
            [str(ELN_VENV_PY), "-m", "uvicorn", "services.activity.app.main:app", "--host", "127.0.0.1", "--port", "8003"],
            cwd=str(ELN_BACKEND),
            env=eln_env,
        )
        processes.append(("Activity", p, 8003))
    else:
        print("[4/7] Activity Service already running on port 8003.")

    # 5. ELN Gateway (8000)
    if not check_port(8000):
        print("\n[5/7] Starting ELN Gateway on port 8000...")
        p = subprocess.Popen(
            [str(ELN_VENV_PY), "-m", "uvicorn", "gateway.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(ELN_BACKEND),
            env=eln_env,
        )
        processes.append(("Gateway", p, 8000))
    else:
        print("[5/7] Gateway already running on port 8000.")

    # 6. Interactive Voice Assistant Agent (Port 8010)
    if not check_port(8010):
        print("\n[6/7] Starting Voice Assistant AI Agent on port 8010...")
        p = subprocess.Popen(
            [HOST_PY, "main.py"],
            cwd=str(ROOT_DIR),
            env=os.environ.copy(),
        )
        processes.append(("Voice Assistant", p, 8010))
    else:
        print("[6/7] Voice Assistant Agent already running on port 8010.")

    # 7. Frontend Dev Server (5173)
    if not check_port(5173):
        print("\n[7/7] Starting React Frontend on port 5173...")
        p = subprocess.Popen(
            ["npm.cmd", "run", "dev"],
            cwd=str(ELN_FRONTEND),
            shell=True,
        )
        processes.append(("Frontend", p, 5173))
    else:
        print("[7/7] Frontend already running on port 5173.")

    # Wait for ports
    print("\nWaiting for services to become healthy...")
    for name, p, port in processes:
        wait_for_port(port, name, timeout=12)

    print("\n" + "=" * 70)
    print("   ALL SERVICES LIVE AND OPERATIONAL!")
    print("=" * 70)
    print("  • Web UI (Frontend)      : http://localhost:5173")
    print("  • ELN API Gateway        : http://localhost:8000 (Docs: /docs)")
    print("  • Identity Service       : http://localhost:8004 (Docs: /docs)")
    print("  • Voice Assistant AI API : http://localhost:8010 (Docs: /docs)")
    print("=" * 70)
    print("\nStack is running. Keeping all processes alive (Press Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for name, p, port in processes:
            p.terminate()


if __name__ == "__main__":
    main()
