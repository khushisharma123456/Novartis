"""
🚀 UNIFIED BACKEND STARTUP
Runs both Flask backend and WhatsApp agent backend together
"""

import subprocess
import sys
import time
from threading import Thread

def run_flask_backend():
    """Run Flask backend on port 5000"""
    print("🌐 Starting Flask Backend (port 5000)...")
    subprocess.run([sys.executable, "backend/app.py"])

def run_whatsapp_agent():
    """Run WhatsApp agent backend on port 8000"""
    print("📱 Starting WhatsApp Agent Backend (port 8000)...")
    subprocess.run(["uvicorn", "agentBackend:app", "--host", "0.0.0.0", "--port", "8000"])

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 STARTING MEDICATION SAFETY BACKEND")
    print("=" * 60)
    print("\nComponents:")
    print("  1. Flask Backend (Main API) - http://localhost:5000")
    print("  2. WhatsApp Agent - http://localhost:8000")
    print("  3. DataQualityAgent - Integrated with Flask")
    print("\n" + "=" * 60)
    
    # Start Flask in a thread
    flask_thread = Thread(target=run_flask_backend, daemon=True)
    flask_thread.start()
    
    time.sleep(2)  # Let Flask start first
    
    # Start WhatsApp agent in main thread
    try:
        run_whatsapp_agent()
    except KeyboardInterrupt:
        print("\n\n⛔ Shutting down backends...")
        sys.exit(0)
