import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

def get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.status, json.loads(res.read().decode())

def post(endpoint, data):
    url = f"{BASE_URL}{endpoint}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.status, json.loads(res.read().decode())

def run_tests():
    print("=== TESTING REST API ENDPOINTS ===")
    
    # 1. Health
    s, data = get("/health")
    print(f"1. GET /health -> {s} | status={data.get('status')}")
    assert s == 200 and data.get("status") == "ok"

    # 2. Subsystem Health
    s, data = get("/api/v1/health")
    print(f"2. GET /api/v1/health -> {s} | status={data.get('status')} | subsystems={list(data.get('subsystems', {}).keys())}")
    assert s == 200

    # 3. Voice Agent Status
    s, data = get("/api/v1/voice-agent/status")
    print(f"3. GET /api/v1/voice-agent/status -> {s} | active_calls={data.get('active_calls')} | audiosocket={data.get('audiosocket_port')}")
    assert s == 200

    # 4. Weather Locations
    s, data = get("/api/v1/weather/locations")
    locs_count = len(data) if isinstance(data, list) else len(data.get('locations', []))
    print(f"4. GET /api/v1/weather/locations -> {s} | locations_count={locs_count}")
    assert s == 200 and locs_count > 0

    # 5. Weather Forecast
    s, data = get("/api/v1/weather/forecast?lat=9.6&lon=41.86&location=Dire%20Dawa")
    temp = data.get("forecast", {}).get("temperature_current_c")
    spraying_safe = data.get("spray_risk", {}).get("is_safe_to_spray")
    print(f"5. GET /api/v1/weather/forecast -> {s} | current_temp={temp}°C | is_safe_to_spray={spraying_safe}")
    assert s == 200

    # 6. Yield Predict
    s, data = post("/api/v1/yield/predict", {
        "crop": "teff",
        "soil_type": "Vertisol (ጥቁር አፈር)",
        "woreda": "Adama",
        "farm_size_ha": 2.0,
        "npsb_kg_ha": 100.0,
        "urea_kg_ha": 50.0
    })
    print(f"6. POST /api/v1/yield/predict -> {s} | projected_yield={data.get('projected_yield_qt_ha')} qt/ha | total={data.get('total_projected_quintals')} qt")
    assert s == 200 and data.get("projected_yield_qt_ha") > 0

    # 7. Calls
    s, data = get("/api/v1/calls")
    calls = data if isinstance(data, list) else data.get("calls", [])
    print(f"7. GET /api/v1/calls -> {s} | calls_count={len(calls)}")
    assert s == 200

    # 8. SMS Inbox
    s, data = get("/api/v1/developer/sms")
    sms_count = len(data) if isinstance(data, list) else len(data.get("messages", []))
    print(f"8. GET /api/v1/developer/sms -> {s} | sms_count={sms_count}")
    assert s == 200

    # 9. Analytics Overview
    s, data = get("/api/v1/analytics/overview")
    print(f"9. GET /api/v1/analytics/overview -> {s} | total_calls={data.get('total_calls')} | grounded_rate={data.get('grounded_answer_rate_pct')}%")
    assert s == 200

    # 10. Admin Analytics
    s, data = get("/api/v1/admin/analytics")
    print(f"10. GET /api/v1/admin/analytics -> {s} | total_calls={data.get('total_calls')}")
    assert s == 200

    # 11. Ask AI (Full RAG + Web + LLM + Guardrails)
    print("\n=== TESTING FULL AI PIPELINE (RAG + WEB + LLM + GUARDRAILS) ===")
    s, data = post("/api/v1/ask", {
        "question": "የስንዴ ዋግ በሽታን ለመከላከል ምን ማድረግ አለብኝ?",
        "language": "am"
    })
    print(f"11. POST /api/v1/ask -> {s}")
    print(f"    Answer: {data.get('answer')[:120]}...")
    print(f"    Grounded: {data.get('grounded')} | Sources count: {len(data.get('sources_used', []))}")
    assert s == 200 and len(data.get("answer", "")) > 10

    print("\n✅ ALL 11 API ENDPOINTS PASSED VERIFICATION!")

if __name__ == "__main__":
    run_tests()
