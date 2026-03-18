import os
from uuid import uuid4
from datetime import date
from rota_service import RotaService
from rota_connector.schemas.project import ProjectCreateSchema

def run_test():
    # 1. Initialize our shiny new RotaService pointing to our local core!
    print("Initializing RotaService...")
    service = RotaService(
        client_id="test_client", 
        client_secret="test_secret", 
        base_url="http://localhost:8000"
    )

    # Let's check the health of the engine first
    print("\nChecking ROTA Backend Health...")
    try:
        health_status = service.check_health()
        print("✅ Core is online:", health_status)
    except Exception as e:
        print("❌ Core offline or unavailable:", e)

    # 2. Let's test calling an admin endpoint to register a new project 
    # (Because it doesn't require prior authentication credentials!)
    rnd_name = f"TestApp-{str(uuid4())[:8]}"
    print(f"\nTesting: Registering a new project named '{rnd_name}'...")
    
    try:
        new_project = service.register_project(
            ProjectCreateSchema(
                name=rnd_name,
                description="A test project created via rota_service.py"
            )
        )
        print("✅ SUCCESS! Project registered.")
        print("Response received from ROTA Core:")
        print(new_project)
        
        # You could now update the service credentials to use these newly generated ones!
        # new_client_id = new_project['client_id']
        # new_secret = new_project['client_secret']
        # service.connector.set_credentials(new_client_id, new_secret)
        
    except Exception as e:
        print(f"❌ ERROR: Failed to reach ROTA Core. Is the backend running on port 8000?")
        print(f"Details: {str(e)}")

if __name__ == "__main__":
    run_test()
