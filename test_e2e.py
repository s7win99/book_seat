"""End-to-end test for the Lab Attendance System."""
import json
import sqlite3
import urllib.request

DB_PATH = r"C:\CODE\project\book_seat\backend\lab_attendance.db"

def api(method, url, data=None, token=None, raw=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        raw_data = resp.read()
        if raw:
            return resp.code, raw_data
        return resp.code, json.loads(raw_data)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def reset_cooldowns():
    """Reset all cooldowns in the database so tests can run without waiting."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM cooldowns")
    conn.commit()
    conn.close()

base = "http://localhost:8000"
results = []

def check(name, expected_code, actual_code, detail=""):
    passed = actual_code == expected_code
    status = "PASS" if passed else "FAIL"
    results.append((name, status))
    extra = f" | {detail}" if detail else ""
    print(f"  [{status}] {name}: got HTTP {actual_code}, expected {expected_code}{extra}")

def check_true(name, value, detail=""):
    status = "PASS" if value else "FAIL"
    results.append((name, status))
    extra = f" | {detail}" if detail else ""
    print(f"  [{status}] {name}: {value}{extra}")


# --- Setup ---
print("=== SETUP: Get tokens ===")
_, r = api("POST", f"{base}/api/auth/login", {"username": "admin", "password": "admin123"})
admin_token = r["access_token"]
print("  Admin token obtained")

_, r = api("POST", f"{base}/api/auth/login", {"username": "zhangsan", "password": "123456"})
zhangsan_token = r["access_token"]
print("  Zhangsan token obtained")

_, r = api("POST", f"{base}/api/auth/login", {"username": "lisi", "password": "123456"})
lisi_token = r["access_token"]
print("  Lisi token obtained")

# Get seat info
_, seats = api("GET", f"{base}/api/admin/seats", token=admin_token)
a1 = next(s for s in seats if s["name"] == "A1")
a2 = next(s for s in seats if s["name"] == "A2")
print(f"  A1 (shared): id={a1['id']}, token={a1['token'][:20]}...")
print(f"  A2 (fixed): id={a2['id']}, assigned to {a2['assigned_user_name']}")

# Cleanup: force checkout anyone who might be checked in, and reset cooldowns
for uid in [5, 6]:
    api("POST", f"{base}/api/admin/force-checkout/{uid}", token=admin_token)
reset_cooldowns()
print("  Cooldowns reset")

# --- Test scenarios ---
print()
print("=== SCENARIO 1: Login as admin (admin/admin123) ===")
code, r = api("POST", f"{base}/api/auth/login", {"username": "admin", "password": "admin123"})
check("Admin login returns 200 with token", 200, code, f"token_present={bool(r.get('access_token'))}")

print()
print("=== SCENARIO 2: Login as zhangsan (zhangsan/123456) ===")
code, r = api("POST", f"{base}/api/auth/login", {"username": "zhangsan", "password": "123456"})
check("Zhangsan login returns 200 with token", 200, code, f"token_present={bool(r.get('access_token'))}")

print()
print("=== SCENARIO 3: List seats ===")
code, all_seats = api("GET", f"{base}/api/seats", token=zhangsan_token)
a1_exists = any(s["name"] == "A1" and s["seat_type"] == "shared" for s in all_seats)
a2_exists = any(s["name"] == "A2" and s["seat_type"] == "fixed" for s in all_seats)
check("List seats returns 200", 200, code)
check_true("A1 (shared) exists in list", a1_exists)
check_true("A2 (fixed) exists in list", a2_exists)

print()
print("=== SCENARIO 4: Check in as zhangsan to shared seat A1 ===")
code, r = api("POST", f"{base}/api/checkin", {"seat_token": a1["token"]}, zhangsan_token)
check("Zhangsan checkin to shared A1 fails (has fixed seat)", 403, code, f"detail={r.get('detail')}")

print()
print("=== SCENARIO 5: Check in as lisi to shared seat A1 ===")
reset_cooldowns()
code, r = api("POST", f"{base}/api/checkin", {"seat_token": a1["token"]}, lisi_token)
check("Lisi checkin to shared A1 succeeds", 200, code, f"msg={r.get('message')}")

print()
print("=== SCENARIO 5b: Verify A1 is occupied by lisi ===")
_, seats_now = api("GET", f"{base}/api/seats", token=admin_token)
a1_now = next(s for s in seats_now if s["name"] == "A1")
check_true("A1 is occupied", a1_now["is_occupied"])
check_true("A1 occupant is Li Si", a1_now["occupant_name"] == "Li Si", f"occupant={a1_now['occupant_name']}")

print()
print("=== SCENARIO 6: Check in as lisi to fixed seat A2 ===")
# Lisi is on A1; trying to switch to A2 should fail (not assigned)
reset_cooldowns()
code, r = api("POST", f"{base}/api/checkin", {"seat_token": a2["token"]}, lisi_token)
check("Lisi checkin to fixed A2 fails (not assigned)", 403, code, f"detail={r.get('detail')}")

print()
print("=== SCENARIO 7: Check out lisi from A1 ===")
reset_cooldowns()
code, r = api("POST", f"{base}/api/checkout", {"seat_id": a1["id"]}, lisi_token)
check("Lisi checkout from A1 succeeds", 200, code, f"msg={r.get('message')}, duration={r.get('duration_minutes')}min")

print()
print("=== SCENARIO 8: Check in zhangsan to his fixed seat A2 ===")
reset_cooldowns()
code, r = api("POST", f"{base}/api/checkin", {"seat_token": a2["token"]}, zhangsan_token)
check("Zhangsan checkin to fixed A2 succeeds", 200, code, f"msg={r.get('message')}")

print()
print("=== SCENARIO 8b: Check in lisi to shared seat A1 (now free) ===")
reset_cooldowns()
code, r = api("POST", f"{base}/api/checkin", {"seat_token": a1["token"]}, lisi_token)
check("Lisi checkin to A1 (now free) succeeds", 200, code, f"msg={r.get('message')}")

print()
print("=== SCENARIO 9: Force checkout lisi as admin ===")
code, r = api("POST", f"{base}/api/admin/force-checkout/6", token=admin_token)
check("Admin force checkout lisi succeeds", 200, code, f"msg={r.get('message')}")

# Clean up zhangsan too
api("POST", f"{base}/api/admin/force-checkout/5", token=admin_token)

print()
print("=== SCENARIO 10: Check leaderboard endpoint ===")
code, r = api("GET", f"{base}/api/attendance/leaderboard?period=week", token=admin_token)
check("Leaderboard (week) returns 200", 200, code, f"entries={len(r)}")
for entry in r[:3]:
    print(f"    #{entry['rank']}: {entry['name']} - rate={entry['attendance_rate']}, valid={entry['valid_count']}, mins={entry['total_minutes']}")

code, r = api("GET", f"{base}/api/attendance/leaderboard?period=month", token=admin_token)
check("Leaderboard (month) returns 200", 200, code, f"entries={len(r)}")

print()
print("=== SCENARIO 11: Check attendance endpoint ===")
code, r = api("GET", f"{base}/api/attendance/my", token=zhangsan_token)
check("Zhangsan my attendance returns 200", 200, code, f"records={len(r)}")

code, r = api("GET", f"{base}/api/admin/attendance", token=admin_token)
check("Admin attendance returns 200", 200, code, f"users={len(r)}")
for u in r[:3]:
    print(f"    {u['name']}: valid={u['total_valid']}, minutes={u['total_minutes']}")

print()
print("=== EXTRA: Checkin status ===")
code, r = api("GET", f"{base}/api/checkin/status", token=zhangsan_token)
check("Zhangsan checkin status", 200, code, f"checked_in={r.get('is_checked_in')}")

code, r = api("GET", f"{base}/api/checkin/status", token=lisi_token)
check("Lisi checkin status", 200, code, f"checked_in={r.get('is_checked_in')}")

print()
print("=== EXTRA: Health check ===")
code, r = api("GET", f"{base}/api/health")
check("Health check", 200, code, f"status={r.get('status')}")

print()
print("=== EXTRA: QR code endpoint ===")
code, raw = api("GET", f"{base}/api/admin/seats/5/qrcode", token=admin_token, raw=True)
check("Seat QR code returns PNG", 200, code, f"size={len(raw)} bytes")

print()
print("=== EXTRA: Auth me endpoint ===")
code, r = api("GET", f"{base}/api/auth/me", token=admin_token)
check("Auth me returns current user", 200, code, f"user={r.get('username')}")

print()
print("=== EXTRA: Change password ===")
# Login as zhangsan again to get fresh token
_, r = api("POST", f"{base}/api/auth/login", {"username": "zhangsan", "password": "123456"})
zhangsan_token = r["access_token"]
code, r = api("POST", f"{base}/api/auth/change-password",
              {"old_password": "123456", "new_password": "newpass123"}, zhangsan_token)
check("Change password succeeds", 200, code, f"msg={r.get('message')}")
# Change back
_, r = api("POST", f"{base}/api/auth/login", {"username": "zhangsan", "password": "newpass123"})
zhangsan_token = r["access_token"]
code, r = api("POST", f"{base}/api/auth/change-password",
              {"old_password": "newpass123", "new_password": "123456"}, zhangsan_token)
check("Change password back succeeds", 200, code)

# Summary
print()
print("=" * 60)
passed = sum(1 for _, s in results if s == "PASS")
failed = sum(1 for _, s in results if s == "FAIL")
print(f"RESULTS: {passed} passed, {failed} failed out of {len(results)} tests")
if failed > 0:
    print("FAILED TESTS:")
    for name, status in results:
        if status == "FAIL":
            print(f"  - {name}")
else:
    print("ALL TESTS PASSED!")
print("=" * 60)
