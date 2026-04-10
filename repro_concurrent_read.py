"""Fire 3 sync triggers, and simultaneously hammer /clients/ + /mcc/overview to catch 500s from concurrent writes/reads."""
import concurrent.futures
import threading
import time
import requests

BASE = "http://127.0.0.1:8000/api/v1"
s = requests.Session()
s.get(f"{BASE}/auth/status", params={"bootstrap": 1})

stop = threading.Event()
errors = []


def hammer_get(path):
    count = 0
    while not stop.is_set():
        try:
            r = s.get(f"{BASE}{path}", timeout=30)
            if r.status_code != 200:
                errors.append((path, r.status_code, r.text[:200]))
        except Exception as e:
            errors.append((path, "EXC", str(e)[:200]))
        count += 1
        time.sleep(0.1)
    print(f"  hammer {path}: {count} requests")


def fire_sync(cid):
    t0 = time.time()
    try:
        r = s.post(f"{BASE}/sync/trigger", params={"client_id": cid, "days": 30}, timeout=120)
        return (cid, r.status_code, round(time.time() - t0, 1), r.text[:200] if r.status_code != 200 else "")
    except Exception as e:
        return (cid, "EXC", round(time.time() - t0, 1), str(e)[:200])


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    # Start hammers
    t1 = ex.submit(hammer_get, "/clients/")
    t2 = ex.submit(hammer_get, "/mcc/overview")
    t3 = ex.submit(hammer_get, "/mcc/overview")
    # Fire 3 parallel syncs
    sync_futures = [ex.submit(fire_sync, cid) for cid in [2, 3, 4]]
    results = [f.result() for f in sync_futures]
    stop.set()

for r in results:
    print(f"sync cid={r[0]} status={r[1]} time={r[2]}s body={r[3]}")

print(f"\nErrors in hammer: {len(errors)}")
for e in errors[:20]:
    print(f"  {e}")
