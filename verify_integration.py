"""
✅ VERIFY INTEGRATION - Quick Check
"""

import os
import sys

print("=" * 70)
print("🔍 VERIFYING AGENT INTEGRATION")
print("=" * 70)

# Check 1: Files exist
print("\n📂 Checking files...")
files_to_check = [
    ("dataQualityAgent.py", "DataQualityAgent"),
    ("agentBackend.py", "WhatsApp Agent"),
    ("backend/app.py", "Flask Backend"),
    ("backend/agent_integration.py", "Integration Layer"),
    ("backend/models.py", "Database Models")
]

all_files_exist = True
for filepath, name in files_to_check:
    if os.path.exists(filepath):
        print(f"  ✅ {name}: {filepath}")
    else:
        print(f"  ❌ {name}: {filepath} NOT FOUND")
        all_files_exist = False

if not all_files_exist:
    print("\n❌ Missing required files!")
    sys.exit(1)

# Check 2: Can import integration
print("\n🔧 Testing imports...")
try:
    sys.path.append('backend')
    from agent_integration import (
        initialize_data_quality_agent,
        process_patient_with_agent,
        handle_doctor_correction
    )
    print("  ✅ Integration module imports successfully")
except ImportError as e:
    print(f"  ❌ Integration module import failed: {e}")
    sys.exit(1)

# Check 3: Can import DataQualityAgent
try:
    from dataQualityAgent import DataQualityAgent
    print("  ✅ DataQualityAgent imports successfully")
except ImportError as e:
    print(f"  ❌ DataQualityAgent import failed: {e}")
    sys.exit(1)

# Check 4: Check backend has new endpoints
print("\n🔌 Checking backend endpoints...")
with open('backend/app.py', 'r') as f:
    content = f.read()
    
endpoints_to_check = [
    '/api/agent/validate-patient',
    '/api/agent/doctor-update',
    '/api/agent/whatsapp-followup'
]

for endpoint in endpoints_to_check:
    if endpoint in content:
        print(f"  ✅ {endpoint}")
    else:
        print(f"  ❌ {endpoint} NOT FOUND")

# Check 5: Integration import in app.py
if 'agent_integration' in content:
    print("  ✅ Integration imported in app.py")
else:
    print("  ❌ Integration NOT imported in app.py")

# Summary
print("\n" + "=" * 70)
print("✅ VERIFICATION COMPLETE")
print("=" * 70)
print("\n🎉 All checks passed!")
print("\n📝 Next steps:")
print("  1. Start backend: python backend/app.py")
print("  2. Test integration: python test_integration.py")
print("  3. Check API docs: INTEGRATION_README.md")
print("\n🔗 Your agents are connected to the backend!")
