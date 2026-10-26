# 🍌 MINION-FORTRESS (KOVAN-X) v3.0

> **Yüksek Başarımlı, Sıfır Gecikmeli (Zero-Lag) Çoklu Ajan Komuta Merkezi & Çift Pencereli TUI Kontrol Kalesi**

MINION-FORTRESS, karmaşık ve çoklu ajan (multi-agent) mimarilerini asenkron olay döngüsü (`asyncio`), Pub/Sub tabanlı `EventBus`, çift yönlü IPC soket yayınları (`Zero-Lag IPC`), dayanıklı halka bellek tamponları (`RingBuffer`) ve `Textual` TUI motoru ile gerçek zamanlı yöneten bir istihbarat ve operasyon kalesidir.

---

## 🌟 Öne Çıkan Yetenekler ve Mimari Bileşenler

| Modül | Açıklama |
|---|---|
| **🪟 Otomatik İkinci Pencere (Detached Monitor)** | İlk pencere (`main.py`) açıldığında otomatik olarak ikinci bir bağımsız işletim sistemi konsol penceresi açar. Çift yönlü TCP IPC soketi (`127.0.0.1:42010`) üzerinden canlı hata ve telemetri akışı sunar. |
| **🚨 Error & Health Monitor** | Tüm ajanlardan gelen `Exception`, HTTP 429 (Rate Limit), HTTP 500 ve RAM/CPU sınır aşım alarmlarını anlık olarak yakalar ve renklendirir. |
| **🔍 Custom Log Sniper** | Binlerce satırlık log akışında canlı Regex taraması yapar; kullanıcı yazdıkça satırları sıfır gecikmeyle filtreleyip sarı renkle parlatır (`highlight`). |
| **🛡️ Auto-Healing & Watchdog** | Her ajanın kalp atışını (`heartbeat`) dinler; 5 saniye yanıtsız kalan veya `ERROR` durumuna düşen ajanları otomatik sonlandırıp temiz state ile ayağa kaldırır (IDLE ajanlar zaman aşımı hatasından muaftır). |
| **⏪ Zaman Yolculuğu (Time Travel)** | Ajanların son 10 veya 50 adımını bellek içi `RingBuffer` üzerinden geri sarıp simüle edilmiş geçmiş adımları incelemenizi sağlar (ekran titremesi olmadan sıfır gecikmeli akış). |
| **🔌 Plugin Hub & Tool Store** | `Docling-v2`, `pgvector-sync` ve `Telegram-Bot` gibi harici araçları canlı olarak açıp kapatmanızı (`Hot-Reload`), ajanların durumuna etki etmesini ve yeni eklentileri dinamik taramanızı sağlar. |
| **📤 Session Snapshot Export** | `F8` tuşuna basıldığında o anki bellek state'ini, telemetriyi ve log havuzunu hem Markdown (`.md`) hem de JSON (`.json`) olarak `/reports/` dizinine kaydeder. |
| **🕹️ İnteraktif Minion REPL** | Ekranın altındaki `minion>` terminalinden `@01 pause`, `@03 error`, `@model switch <ad>`, `detach`, `spawn <isim>` ve `filter <regex>` komutları verilebilir. |
| **🍌 Banana Mode (Panik Tuşu)** | `F12` tuşu veya `banana` komutuyla tüm sistemi güvenli acil durum moduna alır, işleyişi dondurur ve eksiksiz tüm sistem dökümünü diske kaydeder. |

---

## 🏗️ Proje Dizin Yapısı

```text
minion_fortress/
├── core/
│   ├── daemon.py          # Arka plan ajan döngüsü, iş simülasyonu ve Watchdog Auto-Healing
│   ├── event_bus.py       # Asyncio Pub/Sub ve sıfır gecikmeli çift yönlü IPC soket yayını
│   └── state.py           # Thread-safe RingBuffer, MinionState ve FortressState
│
├── ui/
│   ├── app.py             # Ana Textual App, 2x2 grid yerleşimi, otomatik ikinci pencere tetikleyici
│   ├── detached_window.py # Bağımsız ikinci pencere uygulaması (Detached Monitor Node)
│   ├── theme.py           # Minion sarısı (#FFE135), karanlık arka plan ve ANSI stilleri
│   └── panes/
│       ├── error_pane.py  # Özellik 2: Error & Health Monitor
│       ├── sniper_pane.py # Özellik 3: Custom Log Sniper (Live Regex)
│       ├── minion_pane.py # Özellik 6: Ajan terminali & Titremesiz Time Travel Replay
│       └── plugin_pane.py # Özellik 7: Plugin Hub & Canlı Eklenti Bildirimleri
│
├── plugins/
│   ├── docling_tool.py    # Doküman ve tablo çıkarma aracı (Docling-v2)
│   ├── pgvector_tool.py   # Vektör veritabanı senkronizasyonu (pgvector-sync)
│   ├── telegram_tool.py   # Acil durum bildirim botu (Telegram-Bot)
│   ├── openrouter_tool.py # Çoklu LLM ağ geçidi aracı (OpenRouter-API)
│   └── manager.py         # Dinamik eklenti tarayıcısı ve durum yöneticisi
│
├── reports/               # Dışa aktarılan oturum snapshot raporları (.md ve .json)
├── tests/
│   ├── test_minion_fortress.py # Çekirdek birim, IPC broadcast, watchdog ve entegrasyon testleri
│   └── test_ui.py              # Textual UI Pilot ve Detached Monitor testleri
├── detached_monitor.py    # İkinci pencere doğrudan başlatıcı betiği
├── main.py                # Başlatıcı CLI (İki pencereyi otomatik açar)
├── requirements.txt       # Otomatik bağımlılık dosyası
├── run.bat                # Akıllı Windows başlatıcı (Otomatik .venv ve paket kurulumu)
└── pytest.ini             # Test koşum konfigürasyonu
```

---

## 🚀 Kurulum ve Çalıştırma

### 1. Tek Tıkla Başlatma (Windows)
Windows ortamında `run.bat` dosyasına çift tıklayarak çalıştırabilirsiniz. `run.bat`:
- Sanal ortam (`.venv`) yoksa otomatik olarak oluşturur.
- Gerekli paketleri `requirements.txt` üzerinden otomatik yükler.
- Ana Komuta Kalesini açar ve ardından **ikinci monitör penceresini (Detached Window Node)** otomatik olarak ayrı bir konsol penceresinde başlatır!

```cmd
run.bat
```

### 2. Python ile Doğrudan Başlatma
```bash
# İlk pencere açılır ve ikinci pencere otomatik olarak yeni bir konsolda başlatılır:
python main.py

# Yalnızca tek pencere modunda çalıştırmak için:
python main.py --no-detached

# İkinci pencereyi doğrudan bağımsız çalıştırmak için:
python detached_monitor.py
```

### 3. Arka Plan Daemon Modu (Headless)
Arayüz olmadan yalnızca arka plan daemon ve IPC dinleyicisini çalıştırmak için:
```bash
python main.py --daemon
```

### 4. Tek Komutla Anlık Oturum Raporu Alma (Export)
```bash
python main.py --export
```

### 5. Test Paketini Çalıştırma
```bash
pytest tests
```

---

## ⌨️ Kısayol Tuşları (Keybindings)

| Tuş | Eylem |
|---|---|
| **`F12`** | 🍌 **Banana Mode**: Acil durum panik modunu açar/kapatır (Safe lockdown & tam bellek dökümü) |
| **`F8`** | 📤 **Export Session**: Anlık oturum raporunu `.md` ve `.json` formatında kaydeder |
| **`F4`** | 🪟 **Detach Window**: İkinci pencereyi (Detached Monitor Node) ayrı bir pencere olarak yeniden açar |
| **`F5`** | 🔄 **Rescan Plugins**: Eklenti klasörünü yeniden tarayıp araçları günceller |
| **`Ctrl + Q`** | 🛑 **Quit**: Uygulamayı temiz bir şekilde sonlandırır |

---

## 🕹️ Minion REPL Komut Rehberi (Tab-Completion Destekli)

Uygulama açıkken ekranın en altındaki `minion>` çubuğuna yazarken **Tab** tuşuna basarak komutları ve parametreleri otomatik tamamlayabilirsiniz. Örnek komutlar:

* `@01 pause` : ID'si `01` olan ajanı duraklatır.
* `@01 resume` : ID'si `01` olan ajanı devam ettirir.
* `@03 error` : ID'si `03` olan ajanda simüle edilmiş hata tetikler (Watchdog'un oto-kurtarma yeteneğini test etmek için).
* `@01 replay` : İlgili ajanın geçmiş log adımlarını geri sarar.
* `@model switch deepseek-r1` : Seçili ajanın LLM modelini anında değiştirir.
* `detach` : İkinci monitör penceresini (`Pencere 2`) anında yeni bir konsolda açar.
* `banana` : Banana Mode'u açar/kapatır.
* `export` : Oturum raporu çıktısı alır.
* `heal 01` : Watchdog Auto-Healing rutini tetikler.
* `spawn analist-01 qwen-2.5-coder` : Kümeye anında yeni bir minion işçi ekler.
* `filter [ERROR|429]` : Sniper penceresine regex filtresi gönderir.
* `plugin toggle Telegram-Bot` : Belirtilen eklentiyi aktifleştirir veya duraklatır.
* `help` : Komut listesini görüntüler.
