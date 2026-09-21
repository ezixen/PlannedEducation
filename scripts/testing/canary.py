# scripts/testing/canary.py
import requests
import sys
import time

def check_canary():
    print("Running Canary Debug Test for PlannedEducation...")
    
    # Check Backend API Health
    try:
        api_res = requests.get("http://localhost:8000/docs", timeout=5)
        if api_res.status_code == 200:
            print("[OK] Backend API is reachable (http://localhost:8000/docs)")
        else:
            print(f"[FAIL] Backend API returned status {api_res.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Backend API is unreachable: {e}")
        sys.exit(1)
        
    # Check Frontend React App Health
    try:
        web_res = requests.get("http://localhost:5173", timeout=5)
        if web_res.status_code == 200:
            print("[OK] Frontend Portal is reachable (http://localhost:5173)")
        else:
            print(f"[FAIL] Frontend Portal returned status {web_res.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Frontend Portal is unreachable: {e}")
        sys.exit(1)

    print("\n[SUCCESS] Canary tests passed. The local environment is healthy and running.")
    sys.exit(0)

if __name__ == "__main__":
    check_canary()

