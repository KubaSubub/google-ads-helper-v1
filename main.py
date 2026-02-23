"""
Google Ads Helper - Desktop Application Entry Point
PyWebView wrapper for FastAPI backend + React frontend
"""

import webview
import threading
import uvicorn
import os
import sys
import time
import requests

# Detect if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    print(f"Running as frozen executable from: {BASE_DIR}")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"Running in development mode from: {BASE_DIR}")

FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

# CRITICAL: Guard - ensure frontend build exists
if not os.path.exists(FRONTEND_DIST):
    print("\n" + "="*60)
    print("❌ ERROR: Frontend build not found!")
    print("="*60)
    print(f"   Expected directory: {FRONTEND_DIST}")
    print("\n   To fix this, run:")
    print("   1. cd frontend")
    print("   2. npm install")
    print("   3. npm run build")
    print("="*60 + "\n")
    input("Press ENTER to exit...")
    sys.exit(1)

# Import FastAPI app AFTER path setup
# Add backend to Python path if needed
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.main import app as fastapi_app
from fastapi.staticfiles import StaticFiles

# CRITICAL: Mount StaticFiles LAST (after all API routes registered in backend/app/main.py)
# This ensures /api/v1/* routes are not intercepted by catch-all static handler
print(f"Mounting frontend static files from: {FRONTEND_DIST}")
fastapi_app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

# Start uvicorn in background thread
def start_backend():
    """Run FastAPI backend in background thread"""
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False  # Reduce console noise
    )

print("\n" + "="*60)
print("  Starting Google Ads Helper")
print("="*60)

backend_thread = threading.Thread(target=start_backend, daemon=True)
backend_thread.start()

# CRITICAL: Poll /health instead of fixed sleep
# Wait for backend to be ready (max 15s)
print("⏳ Waiting for backend to start...")
backend_ready = False

for i in range(75):  # 75 * 0.2s = 15s max
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if response.status_code == 200:
            print("✅ Backend ready!")
            backend_ready = True
            break
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        time.sleep(0.2)
        if i % 10 == 0 and i > 0:  # Progress indicator every 2s
            print(f"   Still waiting... ({i//5}s)")

if not backend_ready:
    print("\n" + "="*60)
    print("❌ Backend failed to start within 15 seconds")
    print("="*60)
    print("   This may be due to:")
    print("   - Port 8000 already in use")
    print("   - Missing Python dependencies")
    print("   - Database initialization error")
    print("\n   Check logs for details.")
    print("="*60 + "\n")
    input("Press ENTER to exit...")
    sys.exit(1)

print("="*60)
print("🚀 Opening application window...")
print("="*60 + "\n")

# Open PyWebView window
webview.create_window(
    "Google Ads Helper",
    "http://127.0.0.1:8000",
    width=1400,
    height=900,
    resizable=True,
    fullscreen=False,
    min_size=(1024, 768)
)
webview.start()

# When window closes, the app terminates (daemon thread stops automatically)
print("\n" + "="*60)
print("  Application closed. Goodbye!")
print("="*60)
