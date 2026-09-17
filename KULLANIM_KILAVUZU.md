<div align="center">
  <h1>BurpNake Kullanım Kılavuzu</h1>
  <p><b>Otonom Yapay Zeka Destekli Bug Bounty ve Sızma Testi Platformu</b></p>
</div>

<br />

## İçindekiler
- [1. Proje Vizyonu ve Mimari](#1-proje-vizyonu-ve-mimari)
- [2. Temel Yetenekler](#2-temel-yetenekler)
- [3. Sistem Gereksinimleri](#3-sistem-gereksinimleri)
- [4. Kurulum Adımları](#4-kurulum-adımları)
  - [Docker ile Kurulum (Önerilen)](#docker-ile-kurulum-önerilen)
  - [Manuel (Yerel) Kurulum](#manuel-yerel-kurulum)
- [5. Burp Suite Entegrasyonu](#5-burp-suite-entegrasyonu)
- [6. Yapay Zeka (LLM) Konfigürasyonu](#6-yapay-zeka-llm-konfigürasyonu)
- [7. Yasal Uyarı ve Sorumluluk Reddi](#7-yasal-uyarı-ve-sorumluluk-reddi)

---

## 1. Proje Vizyonu ve Mimari

BurpNake, statik zafiyet tarayıcılarının (scanner) aksine, bir güvenlik araştırmacısının zihinsel karar alma süreçlerini (Chain-of-Thought) taklit eden **otonom bir yapay zeka** platformudur. HTTP trafiğini yalnızca metin olarak okumaz; hedef mimariyi anlar, state (durum) takibi yapar ve zafiyetleri dinamik olarak sömürür.

### Mimari Akış:
1. **Veri Yakalama:** Java tabanlı Burp Suite eklentisi, trafiği anlık olarak BurpNake arka ucuna (Backend) iletir.
2. **Pasif Analiz:** Backend, trafiği 88 farklı güvenlik zafiyeti şablonuna göre inceler ve hedefin DOM (Document Object Model) yapısını ayrıştırır.
3. **Otonom Avlanma:** Yapay zeka ajanı, potansiyel zafiyetleri doğrulamak için otomatik olarak mutasyonlu HTTP istekleri oluşturur ve hedefe gönderir.
4. **Raporlama:** Doğrulanan bulgular (Findings), HackerOne / Bugcrowd formatında, Python ve cURL PoC (Proof of Concept) betikleriyle birlikte otomatik olarak hazırlanır.

---

## 2. Temel Yetenekler

* **Semantik DOM Keşfi (Reconnaissance):** Hedef sistemin döndürdüğü HTML kodunu ayrıştırarak (BeautifulSoup & lxml); gizli form alanlarını, geliştirici yorum satırlarını ve gömülü API uç noktalarını (endpoints) bulur. Bu özellik, yapay zekanın var olmayan parametreler uydurmasını (hallucination) engeller.
* **Çok Adımlı Makro (Stateful) Fuzzing:** Otonom ajan, oturum (session) ve çerezleri (cookies) hafızasında tutarak birden fazla adımdan oluşan karmaşık saldırı senaryolarını (Ör: Hesap oluşturma ve ardından yetki yükseltme) icra edebilir.
* **Dinamik Zafiyet Zincirleme (AI Chain Agent):** Sistem arka planında çalışan bir alt-ajan (Sub-Agent), düşük seviyeli (Low/Info) zafiyetleri analiz eder ve bunları LLM'e göndererek yüksek etkili zincirleme saldırılar (Ör: XSS + CORS = Account Takeover) üretir.
* **Kör Zafiyet Analizi (Response Differ):** Hedef sistemin hata mesajı döndürmediği senaryolarda; metin uzunluğu, kelime sayısı ve tepki süresini baz alarak kör zafiyetleri (Blind SQLi, Blind SSRF) büyük bir doğrulukla tespit eder.

---

## 3. Sistem Gereksinimleri

Platformun sorunsuz çalışabilmesi için aşağıdaki yazılımların sisteminizde yüklü olması gerekmektedir:
* **Python 3.12+** (Arka uç ve Yapay Zeka motoru için)
* **Node.js 18+** (React tabanlı gösterge paneli için)
* **Java 11+** (Burp Suite uzantısını yükleyebilmek için)
* **Docker ve Docker Compose** (Konteyner tabanlı kurulum tercih edilecekse)

---

## 4. Kurulum Adımları

### Docker ile Kurulum (Önerilen)
Tüm mimariyi tek bir komutla ve izole bir biçimde ayağa kaldırmak için en güvenilir yöntemdir.

1. Repoyu bilgisayarınıza klonlayın:
   \\\ash
   git clone https://github.com/egnake/Burpnake.git
   cd Burpnake
   \\\
2. Ortam değişkenlerini hazırlayın:
   \\\ash
   cp .env.example .env
   \\\
   Oluşturulan \.env\ dosyasını düzenleyerek kullanmak istediğiniz LLM sağlayıcısının API anahtarını veya yerel adresini girin.
3. Konteynerleri inşa edip başlatın:
   \\\ash
   docker-compose up --build
   \\\
4. Platforma tarayıcınızdan erişin:
   * **Gösterge Paneli (Dashboard):** \http://localhost:3000\
   * **API Dokümantasyonu:** \http://localhost:8899/docs\

### Manuel (Yerel) Kurulum

Sistemi kendi ana makinenizde (bare metal) çalıştırmak isterseniz aşağıdaki adımları izleyin.

#### Arka Uç (Backend) Kurulumu
1. Proje kök dizininde bir sanal ortam oluşturun:
   \\\ash
   python -m venv venv
   \\\
2. Sanal ortamı aktif hale getirin:
   * Windows: \.\venv\Scripts\activate\
   * Linux / macOS: \source venv/bin/activate\
3. Gerekli kütüphaneleri yükleyin:
   \\\ash
   pip install -r requirements.txt
   \\\
4. \.env.example\ dosyasını \.env\ olarak kopyalayıp yapılandırın.
5. Sunucuyu başlatın:
   \\\ash
   python run.py
   \\\

#### Ön Yüz (Frontend) Kurulumu
1. Yeni bir terminal açarak \rontend\ klasörüne geçin:
   \\\ash
   cd frontend
   \\\
2. Bağımlılıkları yükleyin:
   \\\ash
   npm install
   \\\
3. Geliştirici sunucusunu başlatın:
   \\\ash
   npm run dev
   \\\

---

## 5. Burp Suite Entegrasyonu

BurpNake, trafik verisini canlı olarak almak için kendi özel Burp Suite eklentisini kullanır.

1. Cihazınızda Java'nın kurulu olduğundan ve Burp Suite'in çalıştığından emin olun.
2. Burp Suite'te **Extensions** sekmesine, ardından **Installed** alt sekmesine gidin.
3. **Add** butonuna tıklayın.
4. **Extension type** açılır menüsünden **Java** seçeneğini işaretleyin.
5. **Extension file (.jar)** bölümünde klonladığınız dizindeki \connector/BurpNakeConnector.jar\ dosyasını seçin.
6. **Next** diyerek eklentiyi yükleyin. Çıktı ekranında BurpNake sunucusuna (8899 portu) bağlantının başarılı olduğuna dair mesajı görmelisiniz.

---

## 6. Yapay Zeka (LLM) Konfigürasyonu

BurpNake'in otonom ajanları, analiz ve karar alma süreçleri için bir Büyük Dil Modeline (LLM) ihtiyaç duyar. \.env\ dosyası üzerinden aşağıdaki sağlayıcılardan birini veya birkaçını yapılandırabilirsiniz:

* **Ollama (Yerel ve Gizli Yürütme):** Trafiğinizin ve bulgularınızın internete çıkmasını istemediğiniz yüksek güvenlikli hedefler için önerilir.
  * Ollama'yı kurun ve bir kod modeli indirin (Ör: \ollama pull qwen2.5-coder:14b\).
  * \.env\ dosyasına şu satırı ekleyin: \OLLAMA_BASE_URL=http://localhost:11434\
* **Gemini (Bulut Tabanlı):** Karmaşık DOM yapısını anlama ve uzun metinleri (Long Context) işleme kapasitesi sebebiyle en yüksek verimi sunar.
  * Google AI Studio üzerinden bir API anahtarı edinin.
  * \.env\ dosyasına şu satırı ekleyin: \GEMINI_API_KEY=api_anahtariniz\
* **G4F (Ücretsiz Alternatif):** Elinizde herhangi bir API anahtarı bulunmuyorsa, topluluk destekli ücretsiz API ağ geçitlerini kullanabilirsiniz.
  * \.env\ dosyasına şu satırı ekleyin: \G4F_ENABLED=true\ (Not: İstikrarı diğer yöntemlere göre daha düşüktür).

---

## 7. Yasal Uyarı ve Sorumluluk Reddi

BurpNake, münhasıran **yetkili sızma testleri** ve **resmi Bug Bounty programları** (HackerOne, Bugcrowd, vd.) için geliştirilmiş bir siber güvenlik araştırma aracıdır. Yazılım, yetkisiz veya kapsam dışı (Out of Scope) testleri engellemek adına katı yapılandırma kurallarına sahiptir. Proje geliştiricileri; bu yazılımın kötüye kullanımından, neden olabileceği veri kayıplarından veya yasal yaptırımlardan hiçbir koşulda sorumlu tutulamaz. Yazılımı kullanan kişi, tüm yasal sorumluluğu üstlenmiş sayılır.