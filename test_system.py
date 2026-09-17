import os
import sys

# Windows Unicode sorunlarını çözmek için
sys.stdout.reconfigure(encoding='utf-8')

# Proje ana dizinini path'e ekle
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    print("\n" + "="*50)
    print(">> BURPNAKE SISTEM TESTLERI BASLIYOR...")
    print("="*50 + "\n")
    
    passed = 0
    total = 0

    def assert_test(name, condition, error_msg=""):
        nonlocal passed, total
        total += 1
        if condition:
            print(f"[OK] PASS - {name}")
            passed += 1
        else:
            print(f"[FAIL] FAIL - {name} | Detay: {error_msg}")

    try:
        with TestClient(app) as client:
            # 1. API Root ve LLM Durumu
            print("\n--- 1. API & LLM Gateway Kontrolu ---")
            res = client.get("/")
            assert_test("FastAPI Root Endpoint", res.status_code == 200, res.text)
            
            data = res.json()
            llm_status = data.get("llm_providers", {})
            print(f"  > LLM Durumlari: {llm_status}")
            assert_test("En az bir LLM Provider aktif", any(llm_status.values()), "Hicbir LLM yanit vermiyor")

            # 2. Scope Yonetimi
            print("\n--- 2. Scope (Kapsam) Yonetimi Kontrolu ---")
            res = client.post("/api/scope/set", json={
                "program_name": "Test Program",
                "include_domains": ["api.target.com", "*.target.com"],
                "exclude_domains": ["admin.target.com"]
            })
            assert_test("Scope Belirleme (Set)", res.status_code == 200, res.text)

            in_scope = client.post("/api/scope/check", json={"url": "https://api.target.com/v1/users"})
            out_scope = client.post("/api/scope/check", json={"url": "https://admin.target.com/login"})
            wildcard_scope = client.post("/api/scope/check", json={"url": "https://dev.target.com/test"})
            
            assert_test("In-Scope Mantigi", in_scope.json()["in_scope"] is True)
            assert_test("Out-of-Scope (Exclude) Mantigi", out_scope.json()["in_scope"] is False)
            assert_test("Wildcard (*) Mantigi", wildcard_scope.json()["in_scope"] is True)

            # 3. HTTP Ice Aktarma (Import)
            print("\n--- 3. HTTP Parser ve Import Kontrolu ---")
            raw_req = "POST /api/user/123 HTTP/1.1\r\nHost: api.target.com\r\nContent-Type: application/json\r\n\r\n{\"role\":\"admin\"}"
            raw_resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"success\"}"
            
            res = client.post("/api/import/raw", json={"request": raw_req, "response": raw_resp})
            assert_test("Raw HTTP Ice Aktarma", res.status_code == 200, res.text)
            
            exchange_id = res.json()["exchange_id"]
            ex_details = client.get(f"/api/import/exchanges/{exchange_id}")
            assert_test("HTTP Detaylari Getirme", ex_details.status_code == 200)
            
            req_data = ex_details.json()["request"]
            assert_test("Host Dogru Parse Edildi", req_data["host"] == "api.target.com")
            assert_test("JSON Body Dogru Parse Edildi", "role" in req_data["body"])

            # 4. PoC ve Rapor Motoru
            print("\n--- 4. Zafiyet Rapor ve PoC Uretimi Kontrolu ---")
            print("  > Not: Bu adim LLM entegrasyonunu test ettigi icin 10-20 saniye surebilir...")
            
            report_res = client.post("/api/report/generate", json={
                "title": "IDOR leading to Account Takeover",
                "vuln_type": "idor",
                "severity": "high",
                "description": "User can modify role parameter in JSON body to become admin.",
                "impact": "Full account takeover and privilege escalation.",
                "affected_url": "https://api.target.com/api/user/123",
                "affected_parameter": "role",
                "steps_to_reproduce": ["Login as normal user", "Send POST request to /api/user/123", "Change role to admin"],
                "platform": "hackerone"
            })
            
            assert_test("Rapor ve PoC API Cagrisi", report_res.status_code == 200, report_res.text)
            if report_res.status_code == 200:
                rep_data = report_res.json()
                assert_test("HackerOne Formatinda Dosya Kaydedildi", "file_path" in rep_data and "report_" in rep_data["report_id"])
                assert_test("PoC Verisi Dondu", "curl" in rep_data.get("poc", {}))
                print(f"  > Uretilen Rapor Dizini: {rep_data['file_path']}")

    except Exception as e:
        print(f"\n[FATAL ERROR] Testler sirasinda kritik bir hata olustu: {str(e)}")

    print("\n" + "="*50)
    print(f"TEST SONUCU: {passed}/{total} BASARILI")
    print("="*50 + "\n")
    
if __name__ == "__main__":
    run_tests()
