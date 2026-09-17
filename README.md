# 🐍 BurpNake v2.5.0 - Autonomous AI Bug Bounty Hunter

> **Bul -> Analiz Et -> Zincirle -> Exploit Et -> PoC Yaz — Tamamen Otonom**

BurpNake, sıradan bir proxy veya statik tarayıcı değildir. O, bir Bug Bounty Hunter'ın zihinsel süreçlerini (Chain-of-Thought) taklit eden, **State-Machine Fuzzing** yapabilen, **DOM Recon** ile hedefin haritasını çıkaran ve bulduğu açıkları **AI Chain Agent** ile birleştirip kritik zafiyetlere (RCE, ATO, SSRF) dönüştüren elit bir siber güvenlik yapay zekasıdır.

---

## 🚀 Yeni Neler Var? (v2.5 Mega Update)

1. **Akıllı DOM Analizi (Zero-Blindness Recon):** Hedefin HTTP yanıtlarını düz metin olarak okumaz. eautifulsoup4 ile HTML ağacını (AST) çıkartıp gizli <input type="hidden"> formlarını, geliştirici yorumlarını (<!-- -->) ve satır içi JS değişkenlerindeki (Inline API keys/endpoints) gizli API rotalarını keşfeder.
2. **Çok Adımlı (Multi-Step) Makro Saldırıları:** IDOR veya yetki yükseltme (Privilege Escalation) gibi açıklar için Ajan, tek bir istek yerine bir "İstek Zinciri (Macro)" kurabilir. Birinci adımdaki JSON sonucunu (id=45) çekip ikinci adımdaki URL'ye enjekte eder. State ve session çerezleri otomatik korunur.
3. **Dinamik Zafiyet Zincirleme (AI Chain Agent):** Arka planda çalışan alt-ajan, sistemde bulunan düşük seviyeli (Low/Info) zafiyetleri gruplar ve LLM'e sorar: *"Bir Self-XSS ve Open Redirect bulduk, bunları birleştirip Account Takeover (ATO) yaratabilir miyiz?"* Başarılı olursa otomatik Python PoC scriptini yazar.
4. **Kör Zafiyet Avcısı (Response Differ):** Ekrana hata basmayan (Blind SQLi, Blind SSRF) açıkları tespit etmek için kelime sayısı (word count), yanıt boyutu ve saniye bazlı gecikme (time delay) farklılıklarını diferansiyel analize sokar.

---

## 🛠️ Mimari & Çalışma Mantığı

`	ext
Burp Suite (Connector JAR) / HAR Import
    ↓  POST /api/import/live
FastAPI Backend (port 8899)
    ↓  Pasif Analiz (DOM Recon + 88 Vulnerability Pattern)
Otonom Agent Loop (State-Machine Macro Fuzzer)
    ↓  Kör Nokta Analizi (Response Differ)
Zafiyet Zincirleme (AI Chain Builder Sub-Agent)
    ↓  Açık doğrulandı! (Critical/High)
HackerOne / Bugcrowd Raporu + PoC Scripti -> Dashboard
`

---

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Python 3.12+
- Node.js 18+ (Frontend için)
- API Key (OpenAI, Gemini, Anthropic) veya Yerel **Ollama**

### 1. Backend Kurulumu

`ash
git clone https://github.com/yourusername/burpnake.git
cd burpnake
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
# source venv/bin/activate

pip install -r requirements.txt
# .env dosyasını ayarlayın (GEMINI_API_KEY veya Ollama)
python run.py
`

### 2. Frontend Kurulumu (Yeni Terminal)

`ash
cd frontend
npm install
npm run dev
`

### 3. Docker (Tek Komutla Başlat)
`ash
docker compose up --build
`
- Dashboard: http://localhost:3000
- API Docs: http://localhost:8899/docs

---

## 🧠 LLM Motorları

Sistem esnek bir LLM Gateway (Ağ Geçidi) kullanır. Context Window dolduğunda veya API Rate Limit aşıldığında diğerine geçer:
- **Ollama (Yerel/Offline):** qwen2.5-coder:14b veya llama3 önerilir. Gizlilik kritik hedefler için.
- **Gemini:** gemini-1.5-pro (Gelişmiş DOM analizi ve zincirleme için idealdir).
- **G4F (Ücretsiz):** API anahtarınız yoksa G4F_ENABLED=true yaparak ücretsiz LLM havuzunu kullanabilirsiniz.

---

## ⚔️ Gelişmiş Özellikler & Savunma Atlatma
- **OOB (Out-of-Band) Entegrasyonu:** SSRF ve Blind RCE için Burp Collaborator veya Interactsh payload'larını asenkron olarak doğrular.
- **WAF/CDN Bypass Tespiti:** Ajan 403 Forbidden yediğinde pes etmez; HTTP Parameter Pollution (HPP), Null Byte Enjeksiyonu, Chunked Encoding gibi tekniklere (Evasion) başvurur.
- **Kümülatif Mutasyon (Cumulative Fuzzing):** Ajanın gönderdiği payload'lar hedeften gelen yanıta göre sürekli evrim geçirir (Genetic Fuzzing yaklaşımı).

---

## ⚖️ Yasal Uyarı

> [!WARNING]
> BurpNake, **yalnızca yetkili penetrasyon testleri ve resmi Bug Bounty programları** (HackerOne, Bugcrowd, vb.) için geliştirilmiştir. Hedefin belirlediği Scope (Kapsam) dışındaki domainlere saldırmamak üzere kodlanmıştır (scope_manager.py). Geliştiriciler yetkisiz veya yasadışı kullanımdan doğacak sonuçlardan sorumlu değildir.

---
**Lisans:** MIT License