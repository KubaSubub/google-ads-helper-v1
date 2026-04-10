"""Stress test: fire many parallel /sync/trigger calls and observe 500s."""
import concurrent.futures
import time
import sys
import json

import requests

BASE = "http://127.0.0.1:8000/api/v1"

# Bootstrap session
s = requests.Session()
r = s.get(f"{BASE}/auth/status", params={"bootstrap": 1})
print(f"bootstrap: {r.status_code}")
assert r.status_code == 200

# Get list of clients
r = s.get(f"{BASE}/clients/")
clients = [c["id"] for c in r.json().get("items", []) if c["id"] != 1]
print(f"clients (non-demo): {clients}")


def fire_sync(cid: int) -> dict:
    t0 = time.time()
    try:
        r = s.post(
            f"{BASE}/sync/trigger",
            params={"client_id": cid, "days": 30},
            timeout=120,
        )
        elapsed = time.time() - t0
        return {
            "cid": cid,
            "status": r.status_code,
            "elapsed": round(elapsed, 1),
            "body": r.text[:300] if r.status_code != 200 else "",
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {"cid": cid, "status": "EXCEPTION", "elapsed": round(elapsed, 1), "body": str(e)[:300]}


# Run 2 rounds: first with 3 parallel (matches frontend), second with 5 (more stress)
for n in [3, 5]:
    print(f"\n===== round: {n} parallel syncs =====")
    targets = (clients * ((n // len(clients)) + 1))[:n]
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(fire_sync, cid) for cid in targets]
        results = [f.result() for f in futures]
    for r in results:
        print(f"  cid={r['cid']} status={r['status']} time={r['elapsed']}s body={r['body']}")
