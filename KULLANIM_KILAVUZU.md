# BurpNake v2.0.0 — Kapsamli Kullanim Kilavuzu

## Icindekiler

1. [Sistem Mimarisi ve Veri Akisi](#1-sistem-mimarisi-ve-veri-akisi)
2. [Kurulum Rehberi](#2-kurulum-rehberi)
3. [Burp Suite Connector](#3-burp-suite-connector)
4. [Pasif Analiz Motoru](#4-pasif-analiz-motoru-88-pattern)
5. [Otonom Ajan Dongusu](#5-otonom-ajan-dongusu-en-onemli-ozellik)
6. [Arayuz Modullerinin Kullanimi](#6-arayuz-modullerinin-kullanimi)
7. [LLM Entegrasyonu](#7-llm-entegrasyonu-ve-yapilandirma)
8. [Docker ile Kullanim](#8-docker-ile-kullanim)
9. [Yeni Kural Ekleme](#9-yeni-kural-ekleme-gelistirici-rehberi)
10. [Sikca Karsilasilan Sorunlar](#10-sikca-karsilasilan-sorunlar)

---

## 1. Sistem Mimarisi ve Veri Akisi

```
[Burp Suite] -- IHttpListener --> [BurpNakeConnector.jar]
                                          |
                                POST /api/import/live
                                          |
                               [FastAPI Backend :8899]
                                          |
                                  [dedup_filter.py]
                                  (statik asset atla)
                                          |
                                  [SQLite DB: exchanges]
                                  interest_level='pending'
                                          |
                              [passive_analyzer.py - 10 sn loop]
                              88 pattern triage
                                          |
                           interest_level='critical/interesting'
                                          |
                              [agent_loop.py - YENI!]
                              Otonom exploit dongusu
                                          |
                           Max 5 iterasyon -- confirmed?
                                   YES              NO
                                    |               |
                           [save_finding]      [give_up log]
                           [PoC + Rapor]
                                    |
                           [event_broadcaster.py]
                                SSE
                                    |
                           [React Frontend :3000]
                           Dashboard + bildirim
```

---

## 2. Kurulum Rehberi

### Secnek A: Docker (Her PC'de Calisir)

Docker Desktop kurulu olmali: https://docker.com/products/docker-desktop

```bash
git clone https://github.com/yourusername/burpnake.git
cd burpnake

# Konfigurasyonu hazirla
cp .env.example .env
# .env icinde en az bir LLM ayarla (bak Bolum 7)

# Baslat (ilk sefer 5-10 dk surabilir)
docker compose up --build

# Arka planda calistirmak icin
docker compose up -d --build
```

Servisler:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8899
- API Docs: http://localhost:8899/docs

Durdurmak icin: `docker compose down`
Loglar icin: `docker compose logs -f backend`

### Secnek B: Manuel (Windows)

```powershell
# Python 3.12+ gerekli
python --version

cd burpnake
python -m venv venv
.\venv\Scripts\activate

# Bagimliliklar
pip install -r requirements.txt

# .env hazirla
copy .env.example .env
notepad .env

# Backend baslat
python run.py
# Backend: http://localhost:8899
```

```bash
# Ayri terminal - Frontend
cd burpnake\frontend
npm install    # Ilk sefer
npm run dev
# Frontend: http://localhost:3000
```

Ya da `start.bat` ile ikisi birden baslatilir.

---

## 3. Burp Suite Connector

### Kurulum

1. Burp Suite'i ac
2. **Extensions > Installed > Add**
3. Extension Type: **Java**
4. Select File: proje klasoru icindeki `connector/BurpNakeConnector.jar`
5. **Next** tiklayan, Output sekmesinde su gormeli:
   ```
   [BurpNake] Baglandi! Backend: http://127.0.0.1:8899
   ```

### Kontrol

Backend calisiyor mu?
```
GET http://127.0.0.1:8899/api/import/live-status
```
Cevap: `{"status": "online", "app": "BurpNake", ...}`

### Olasi Sorunlar

| Hata | Cozum |
|------|-------|
| `Connection refused` | `python run.py` ile backend'i baslat |
| `Java version error` | JDK 11+ kur: https://adoptium.net |
| Trafik gelmiyor | Burp'te HTTPS trafikler icin CA sertifikasi yukle |

### Docker ile Burp Connector Kullanimi

Docker kullaniyorsaniz Connector, container icindeki backend'e degil **host makinenizin** 8899 portuna ulasir. Bu varsayilan olarak dogru ayarlidir (8899 portu host'a map edilmistir).

---

## 4. Pasif Analiz Motoru (88 Pattern)

`app/modules/passive_analyzer.py` her 10 saniyede bir calisir.

### Nasil Calisir?

1. `interest_level='pending'` olan exchange'leri ceker
2. Her exchange uzerinde 88 vulnerability pattern'ini uygular
3. Puan hesaplar; esige gore seviye atar:
   - `score >= 85` → **critical** (SSE + LLM analiz + Agent Loop)
   - `score >= 45` → **interesting** (SSE bildirimi)
   - `score >= 20` → **low**
   - Alti → **normal**
4. Critical/interesting ise SSE ile frontend'e anlık bildirim gonder

### Tespit Edilen Vulnerability Tipleri

| Kategori | Pattern'ler |
|----------|------------|
| Injection | SQLi (error/blind/time), NoSQLi, XSS (reflected/stored), SSTI, CRLF |
| Server-Side | SSRF (cloud metadata dahil), SSRF via WebRTC, LFI/RFI, RCE, XXE |
| Auth | IDOR (+ unauthenticated bonus), JWT alg:none, OAuth CSRF, SAML wrapping |
| Modern | Log4Shell/JNDI, Prototype Pollution, Deserialization (Java/PHP/Python) |
| Enterprise | HTTP Request Smuggling, Cache Poisoning, gRPC, GraphQL injection/DoS |
| Misc | LLM Prompt Injection, NGINX off-by-slash, Spring Actuator leak |

### Contextual vs. Regex

Basit tarayicilardan farki:
- XSS: Sadece `<script>` gormekle kalmaz, Content-Type'in `text/html` oldugunu ve payload'in **gercekten yansiyip yansimadigi**ni kontrol eder
- SQLi: Response body'deki `sqlite3.operationalerror`, `ORA-` gibi hata mesajlarini arar
- IDOR: URL'de ID varsa header'larda Authorization/Cookie olup olmadigini kontrol eder

---

## 5. Otonom Ajan Dongusu (En Onemli Ozellik!)

### Nedir?

BurpNake'in v2.0.0 ile gelen en kritik ozelligi. passive_analyzer kritik bir exchange tespit ettiginde **agent_loop.py** devreye girer ve sunu yapar:

```
Tur 1: AI → "SQLi gorunuyor, tek tirnak gonderelim" → POST /api/... id=1'
Yanit: 200 OK, normal HTML

Tur 2: AI → "WAF yok gibi, UNION SELECT deneyelim" → POST /api/... id=1 UNION SELECT 1--
Yanit: 500 Internal Server Error + "syntax error near..."

AI: "DATABASE ERROR ALINDI! Bu SQLi confirmed!"
→ Severity: High
→ Bounty Tahmini: $500-$3000
→ curl PoC otomatik yazildi
→ Python exploit scripti otomatik yazildi
→ SSE: "ACIK BULUNDU!" bildirimi
```

### Manuel Tetikleme

```bash
# Belirli bir exchange'i avla
curl -X POST http://localhost:8899/api/agent/hunt \
  -H "Content-Type: application/json" \
  -d '{"exchange_id": "uuid-buraya"}'

# Kuyruktaki tum critical/interesting exchange'leri avla  
curl -X POST http://localhost:8899/api/agent/auto-hunt-all

# Kuyrugu goster
curl http://localhost:8899/api/agent/auto-hunt-queue

# Agent durumu
curl http://localhost:8899/api/agent/status
```

### AI Karar Protokolu

Agent her iterasyonda AI'dan JSON formatinda karar ister:

```json
{
  "decision": "try_payload",  // try_payload | confirmed | give_up
  "reasoning": "Response'da 500 error aldik, SQL hatasi gorunuyor...",
  "payload_modifications": {
    "body": "id=1 UNION SELECT 1,2,3--"
  },
  "success_indicators": ["syntax error", "mysql_fetch"],
  "poc_curl": "curl -X POST ...",
  "severity": "high",
  "bounty_estimate": "$500-$3000"
}
```

---

## 6. Arayuz Modullerinin Kullanimi

### Dashboard (/)
- Toplam exchange, kritik sayisi, finding istatistikleri
- En cok vurulan endpoint'ler (Top 10)
- Son bulgular listesi

### Live Feed (/live)
- SSE ile gelen tum olaylari gosterir
- Renk kodlamasi: Kirmizi = critical, Turuncu = interesting
- "ACIK BULUNDU!" bildirimleri burada anlık cikinar
- Tarayici bildirimi: Critical bulgularda push notification

### AI Hunter Terminal (/hunt)
- **Sol panel:** Tüm exchange'ler (skor ve level ile)
- **Sag panel:** AI chat terminali
- Exchange secip "Analyze" diyerek manual analiz baslat
- Kendi sualini yazabilirsin: "Bu iki endpoint arasinda privilege escalation var mi?"

### Findings (/findings)
- Tüm onaylanmis ve AI analiz edilmis bulgular
- Severity, tarih, AI provider filtreleme
- Bulguya tiklayarak PoC ve tam raporu goster

### Param Discovery (/params)
- Sistemden gecen tüm GET/POST/JSON parametrelerini toplar
- Riskli parameter'lari (redirect_uri, admin, token) otomatik isaretler
- Attack surface genel bakisi

### Scope Manager (/scope)
- HackerOne handle gir (ornek: tesla, yahoo)
- Backend GraphQL API ile tüm in-scope domain'leri ceker
- Program scope'u DB'ye otomatik kaydeder

### Data Import (/import)
- Burp XML export dosyasi yukle (trafik kaydini import et)
- HAR dosyasi yukle (browser dev tools export)
- Toplu trafik analizi icin kullanisli

---

## 7. LLM Entegrasyonu ve Yapilandirma

### Priority Sirasi

```
1. Ollama (OLLAMA_BASE_URL erisilebilirse)
   ↓ Basarisiz
2. Gemini (GEMINI_API_KEY varsa)
   ↓ Basarisiz
3. g4f (G4F_ENABLED=true ise)
   ↓ Hepsi basarisiz
HATA: "All LLM providers failed"
```

### Ollama Modeli Secimi

| Model | RAM | Kalite | Hiz |
|-------|-----|--------|-----|
| qwen2.5-coder:14b | 16GB | Cok Iyi | Orta |
| gemma2:9b | 12GB | Iyi | Hizli |
| llama3.1:8b | 10GB | Orta | Cok Hizli |
| qwen2.5-coder:7b | 8GB | Orta | Hizli |

### .env Yapilandirmasi

```ini
# Ollama (Yerel)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_FALLBACK_MODEL=gemma2:9b

# Gemini (API Key al: makersuite.google.com)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash

# g4f (yedek)
G4F_ENABLED=true

# Uygulama
APP_HOST=0.0.0.0
APP_PORT=8899
DEBUG=false
```

---

## 8. Docker ile Kullanim

### Diger PC'de Kullanim

```bash
# 1. Repo klonla
git clone <repo_url>
cd burpnake

# 2. .env olustur
cp .env.example .env

# 3. Baslat
docker compose up --build

# 4. Burp Connector'i kur (lokal makinede Burp kullaniyorsaniz)
# connector/BurpNakeConnector.jar
```

### Ollama Docker ile Kullanim

Ollama lokal makinende kuruluysa:

**Windows/Mac Docker Desktop:**
```ini
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Linux:**
```ini
OLLAMA_BASE_URL=http://172.17.0.1:11434
```

Ya da docker-compose.yml icindeki `extra_hosts` ayari bunu otomatik yapar.

### Volume Yonetimi

```bash
# Veritabanini yedekle
docker cp burpnake_backend:/app/data/burpnake.db ./backup.db

# Veritabanini sifirla
docker volume rm burpnake_data
docker compose up -d
```

---

## 9. Yeni Kural Ekleme (Gelistirici Rehberi)

`app/modules/passive_analyzer.py` dosyasinda iki yer var:

### 1. Puan Tablosuna Ekle

```python
RULES = {
    # ... mevcut kurallar ...
    "graphql_introspection": 70,  # Yeni kural
}
```

### 2. triage_exchange() icine Algilama Mantigi

```python
# GraphQL Introspection Leak
GRAPHQL_INTRO_PATTERNS = [r"(?i)__schema", r"(?i)IntrospectionQuery"]
for p in GRAPHQL_INTRO_PATTERNS:
    if re.search(p, full, re.IGNORECASE):
        score += RULES["graphql_introspection"]
        matched.append("graphql_introspection (Confirmed)")
        break
```

Sunucuyu yeniden baslat: `python run.py`  
Kural otomatik devreye girer.

---

## 10. Sikca Karsilasilan Sorunlar

### Backend baslamıyor

```
pydantic_core.ValidationError: extra inputs not permitted
```
**Cozum:** `.env` dosyasinda BOM karakteri var. Su komutla temizle:
```powershell
$c = [System.IO.File]::ReadAllText(".env")
[System.IO.File]::WriteAllText(".env", $c.TrimStart([char]65279), [System.Text.UTF8Encoding]::new($false))
```

### Burp Connector trafik gondermiyor

1. Backend calistigindan emin ol: `http://localhost:8899/health`
2. Burp'te Extensions sekmesinde Connector'in output'una bak
3. `GET /api/import/live-status` ile kontrol et

### LLM cevap vermiyor

- Ollama: `ollama list` ile modelin yuklu oldugunu dogrula
- Gemini: API key limiti asiliyor olabilir, g4f'yi aktifle
- g4f: Bazi provider'lar intermittent. g4f version'unu guncelle

### Docker Ollama'ya ulasmiyor

`.env` icinde:
- Windows/Mac: `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- Linux: `OLLAMA_BASE_URL=http://172.17.0.1:11434`

---

**Mutlu Avlar & Guvenli Hacking! 🐍🛡️**