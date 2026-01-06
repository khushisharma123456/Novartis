try:
    from backend.models import db, User, Patient
    print("Import Successful")
except ImportError as e:
    print(f"Import Failed: {e}")
except Exception as e:
    print(f"Error: {e}")
