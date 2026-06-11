import json
import requests

def test_header(title):
    line = "=" * 50
    print(f"\n{line}\n{title}\n{line}")

test_header("TEST 4: POST /api/analyze")
url = "http://127.0.0.1:8000/api/analyze"
file_path = "/Users/corollaguy/Desktop/obd/data/raw/2017-07-14_Seat_Leon_KA_KA_Frei.csv"
try:
    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(url, files=files)
        print(f"Status Code: {resp.status_code}")
        data = resp.json()
        print(json.dumps(data, indent=2))
        session_id = data.get("sessionId")
except Exception as e:
    print(f"Error: {e}")
    session_id = None

if session_id:
    test_header("TEST 5: GET /api/sessions")
    resp = requests.get("http://127.0.0.1:8000/api/sessions")
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
    
    test_header("TEST 6: GET /api/sessions/{id}/dashboard")
    resp = requests.get(f"http://127.0.0.1:8000/api/sessions/{session_id}/dashboard")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print("Keys:", list(data.keys()))
    print("vehicleInfo:", json.dumps(data.get("vehicleInfo"), indent=2))
    print("healthScore:", json.dumps(data.get("healthScore"), indent=2))

    test_header("TEST 7: GET /api/sessions/{id}/anomalies")
    resp = requests.get(f"http://127.0.0.1:8000/api/sessions/{session_id}/anomalies")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print("Keys:", list(data.keys()))
    print(f"anomalies count: {len(data.get('anomalies', []))}")
    if data.get("anomalies"):
        print("First anomaly:", json.dumps(data["anomalies"][0], indent=2))
        
    test_header("TEST 8: GET /api/sessions/{id}/telemetry")
    resp = requests.get(f"http://127.0.0.1:8000/api/sessions/{session_id}/telemetry")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    for k, v in data.items():
        print(f"{k} data points: {len(v)}")

    test_header("TEST 9: GET /api/sessions/{id}/sensors")
    resp = requests.get(f"http://127.0.0.1:8000/api/sessions/{session_id}/sensors")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print("Sensors:", data.get("sensors"))
    matrix = data.get("correlation", [])
    print(f"Correlation matrix size: {len(matrix)}x{len(matrix[0]) if matrix else 0}")

    test_header("TEST 10: GET /api/sessions/{id}/report")
    resp = requests.get(f"http://127.0.0.1:8000/api/sessions/{session_id}/report")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print("Keys:", list(data.keys()))
    print(f"healthScore: {data.get('healthScore')}")
    print("executiveInsights:")
    for ins in data.get("executiveInsights", []):
        print(f"- {ins}")

test_header("TEST 12a: Invalid session ID")
resp = requests.get("http://127.0.0.1:8000/api/sessions/invalid-123/dashboard")
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))

test_header("TEST 12b: Empty CSV")
resp = requests.post("http://127.0.0.1:8000/api/analyze", files={"file": ("empty.csv", b"")})
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
