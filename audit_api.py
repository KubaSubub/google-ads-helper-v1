import httpx
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def check_endpoint(name, url):
    try:
        print(f"Checking {name}...", end=" ")
        resp = httpx.get(url, timeout=30)
        if resp.status_code == 200:
            print(f"OK ({len(resp.json()) if isinstance(resp.json(), list) else 'dict'})")
            return True
        else:
            print(f"FAIL ({resp.status_code})")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def audit():
    print("--- API AUDIT START ---")
    results = []
    results.append(check_endpoint("Clients", f"{BASE_URL}/clients/"))
    results.append(check_endpoint("Campaigns (Client 1)", f"{BASE_URL}/campaigns/?client_id=1"))
    results.append(check_endpoint("Search Terms", f"{BASE_URL}/search-terms/?client_id=1&page_size=1"))
    results.append(check_endpoint("Keywords", f"{BASE_URL}/keywords/keywords/?client_id=1&page_size=1"))
    results.append(check_endpoint("Anomalies", f"{BASE_URL}/analytics/anomalies?client_id=1&days=30"))
    results.append(check_endpoint("Semantic Clusters", f"{BASE_URL}/semantic/clusters?client_id=1&days=30&top_n=100"))
    
    success_count = sum(results)
    print(f"--- AUDIT COMPLETE: {success_count}/{len(results)} Passed ---")

if __name__ == "__main__":
    audit()
