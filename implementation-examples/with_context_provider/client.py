import os
from dotenv import load_dotenv
from rota_service import RotaService
from conv2 import StaffProvider, PracticeProvider
from uuid import UUID
from datetime import date

# Load environment variables from .env
load_dotenv()

# 1. Initialize Service with Providers!
service = RotaService(
    client_id=os.getenv("ROTA_CLIENT_ID"), 
    client_secret=os.getenv("ROTA_CLIENT_SECRET"), 
    base_url=os.getenv("ROTA_BASE_URL", "http://localhost:8000"),
    staff_provider=StaffProvider(),
    practice_provider=PracticeProvider()
)

if __name__ == "__main__":
    # Test Health
    print("Checking Health...")
    print(service.check_health())

    # --- DEMO: AUTO-HYDRATION ---
    PRACTICE_ID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    ROLE_ID = UUID("c3d4e5f6-a7b8-9012-cdef-123456789012")
    TARGET_DATE = date(2026, 7, 23)

    print(f"\n🚀 Running Smart Availability for Practice {PRACTICE_ID}...")
    try:
        # Notice we DON'T pass a payload! The service uses StaffProvider to find all staff 
        # for this practice and builds the payload automatically.
        response = service.auto_get_available_staff(
            practice_id=PRACTICE_ID,
            target_date=TARGET_DATE,
            role_id=ROLE_ID
        )
        print("✅ Smart Availability Success!")
        # print(response)
    except Exception as e:
        print("\n❌ Smart Request failed (Expected if backend is down, but hydration worked!)")
        print(f"Error: {str(e)}")

    print("\n🚀 Testing Context Discovery...")
    try:
        # Get contexts for a specific assignment
        STAFF_ID = UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")
        ctx = service.get_assignment_contexts(STAFF_ID, PRACTICE_ID, TARGET_DATE)
        print("✅ Contexts Hydrated from Providers:")
        print(f"--- Staff Weekly Capacity: {ctx['staff_context'].weekly_capacity} hrs")
        print(f"--- Practice Required Hours: {ctx['practice_context'].required_hours} hrs")
    except Exception as e:
        print(f"❌ Context discovery failed: {str(e)}")
