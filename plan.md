İstediğiniz özellikler ve seçtiğiniz kritik modüllerle (Özellikle **Özel Log / Sniper Penceresi**, **Error & Health Monitor**, **Time Travel Replay**, **Plugin Hub**, **Session Export**, **Interactive REPL** ve **Banana Mode**) tam donanımlı **MINION-FORTRESS (KOVAN-X)** mimarisinin uçtan uca uygulama planı aşağıdadır.

Bu plan; çoklu süreç (multi-process), asenkron olay döngüsü (asyncio), IPC (Unix Domain Sockets) ve katmanlı TUI (Textual) yapısıyla **sıfır donma (zero-lag)** garantisiyle tasarlanmıştır.

---

# MINION-FORTRESS v3.0: Kapsamlı Mimari ve Uygulama Planı

## 1. Modüler Yerleşim ve Ekran Planı (Grid Layout)

Sağdaki dinamik çalışma alanı, seçtiğiniz özel pencerelerle (Error Monitor, Custom Logs, Plugin Hub vb.) şu şekilde bölünecektir:

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🍌 MINION FORTRESS v3.0 │ STATUS: BANANA! 🟡 │ Active: 4/5 │ CPU: 18% │ RAM: 2.1GB │ VRAM: 18.4GB │ [PID: 4201]  │
├───────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─ [LEFT: FORTRESS COMMAND] ────┐ │ ┌─ [RIGHT: DYNAMIC TILING WORKSPACE] ──────────────────────────────────────────┐ │
│ │                               │ │ │ ┌─ 🍌 MINION-01 [ast-parser] ────────────┐ ┌─ 🚨 ERROR & HEALTH PANE ────┐ │ │
│ │ 📊 CLUSTER TELEMETRY          │ │ │ │  (o) > AST Nodes mapped: 142       │ │ │ [19:02] ERR: OpenRouter 429 │ │ │
│ │ Tasks: 1420/1445 (98.4%)      │ │ │ │ \|█\| > [PROGRESS] [███████░░░] 75%  │ │ │ [19:03] WARN: RAM usage >80%  │ │ │
│ │ Token Cost: $0.042            │ │ │ │  / \                               │ │ │ Auto-Healing: Restarting... │ │ │
│ │                               │ │ │ └────────────────────────────────────┘ └─────────────────────────────┘ │ │
│ │ 🤖 MINION ROSTER              │ │ │ ┌─ [VERTICAL SPLIT CONTAINER] ─────────────────────────────────────────┐ │ │
│ │  ID  NAME      STATUS  CPU    │ │ │ │ ┌─ 🔍 CUSTOM LOG SNIPER [Regex] ──┐ ┌─ 🔌 PLUGIN HUB / TOOL ────────┐ │ │
│ │  01 ast-parse RUNNING  12%    │ │ │ │ │ Filter: [ERROR|FATAL]           │ │ │ [x] Docling-v2 (Active)       │ │ │
│ │  02 net-mon   IDLE      1%    │ │ │ │ │ > [FATAL] DB connection lost    │ │ │ [x] pgvector-sync (Active)    │ │ │
│ │  03 quant     BUSY     45%    │ │ │ │ │ > [ERROR] Timeout on HTTP 500   │ │ │ [ ] Telegram-Bot (Paused)     │ │ │
│ │  04 doc-ext   PAUSED    0%    │ │ │ │ └─────────────────────────────────┘ └───────────────────────────────┘ │ │
│ └───────────────────────────────┘ └──────────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ minion> _ [Type command or press F12 for Banana Mode / F8 to Export Session]                                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

```

---

## 2. Sistem Mimarisi ve Veri Akışı (Data Pipeline)

Projenin arkasındaki mekanizma **Pub/Sub (Yayıncı/Abone)** modeline dayanır. Ana Daemon arka planda ajanları çalıştırırken, tüm logları ve hata sinyallerini bir `asyncio.Queue` üzerinden TUI arayüzüne dağıtır.

```text
┌────────────────────────────────────────────────────────┐
│                   DAEMON ENGINE CORE                   │
│  - Agent Pool (Qwen / GLM Workers)                     │
│  - State Manager & Checkpointer                        │
│  - Auto-Healer (Watchdog)                              │
└───────────┬────────────────────────────────┬───────────┘
            │ (Asyncio Queue / Pub-Sub)      │ (Unix Socket)
            ▼                                ▼
┌───────────────────────────────┐   ┌──────────────────────────────┐
│  MAIN DASHBOARD (TUI Process) │   │  DETACHED WINDOW NODES       │
│  - Left: Stats & Roster       │   │  - Dedicated Error Pane      │
│  - Right: Tiling Grid         │   │  - Independent Stream View   │
└───────────────────────────────┘   └──────────────────────────────┘

```

---

## 3. Seçilen Özelliklerin Teknik Detayları ve Uygulama Adımları

### Özellik 2: 🚨 Error & Health Monitor Penceresi

* **Görev:** Sistemdeki tüm ajanlardan gelen istisnaları (`Exception`), HTTP hata kodlarını (429, 500) ve RAM/CPU sınır aşım uyarılarını tek bir ekranda toplar.
* **Uygulama:** Her ajan hatası `EventBus` üzerinden bu pencereye düşer. Kırmızı ve sarı tonlarında renklendirilir.

### Özellik 3: 🔍 Özel Log Sniper Penceresi (Live Regex Filter)

* **Görev:** Binlerce satırlık log akışı içinde anlık olarak filtreleme (`Regex` taraması) yapmanızı sağlar.
* **Uygulama:** Textual `Input` bileşeni ile entegre edilir. Kullanıcı harf yazdıkça log havuzu saniyede filtrelenir, eşleşen satırlar sarı renkle (`highlight`) parlatılır.

### Özellik 8: 🛡️ Otomatik Sağlık Kalkanı & Self-Healing

* **Görev:** Yanıt vermeyen (hang) veya `ERROR` durumuna düşen bir ajanı tespit edip otomatik olarak yeniden başlatır.
* **Uygulama:** Daemon içindeki bir `Watchdog` rutini her ajanın kalp atışını (`heartbeat`) dinler. 5 saniye sinyal gelmezse süreci sonlandırıp (`kill`) temiz state ile yeniden spawn eder.

### Özellik 6: ⏪ Zaman Yolculuğu / Log Replay (Time Travel)

* **Görev:** Hatalı bir görevin geçmişteki son 50 adımını adım adım geri sarıp inceleme imkanı sunar.
* **Uygulama:** Her ajan hücresi, loglarını sabit boyutlu bir `RingBuffer` (bellek havuzu) içinde saklar. Replay modunda buffer pointer'ı geriye sarılarak ekrana simüle edilir.

### Özellik 7: 🔌 Eklenti ve Araç Mağazası (Plugin Hub)

* **Görev:** Ajanların kullandığı dış araçları (`Docling-v2`, `pgvector`, `OpenRouter API`) canlı olarak açıp kapatmanızı (`Hot-Reload`) sağlar.
* **Uygulama:** `plugins/` klasöründeki Python modülleri dinamik olarak (`importlib`) taranır ve arayüzdeki listeden yönetilir.

### Özellik 9: 📤 Oturum Dışa Aktarma (Session Snapshot Export)

* **Görev:** Anlık tüm sistem durumunu, logları ve maliyetleri tek tuşla (`F8`) dışa aktarır.
* **Uygulama:** `F8` tuşuna basıldığında o anki bellek state'i temiz bir Markdown veya JSON dosyasına (`/reports/fortress_session_{timestamp}.md`) yazdırılır.

### Özellik 10: 🕹️ İnteraktif Komuta Satırı (Minion REPL Prompt)

* **Görev:** Ekranın altındaki komut satırından doğrudan ajana talimat vermenizi sağlar.
* **Uygulama:** Tab-completion destekli REPL terminali (`minion> `), yazılan komutları (`@agent-01 pause`, `@model switch qwen`) ilgili ajan kuyruğuna iletir.

### Ekstra: 🍌 Banana Mode (Acil Durum Panik Tuşu)

* **Görev:** `F12` tuşuna basıldığında tüm sistemi güvenli moda alır, log akışını dondurur ve verileri diske kaydeder.

---

## 4. Dosya ve Klasör Mimarisi (Project Structure)

Projenizi hayata geçirmek için önerilen Python dosya yapısı:

```text
minion_fortress/
│
├── core/
│   ├── daemon.py         # Arka plan ajan yöneticisi ve Watchdog (Özellik 8)
│   ├── event_bus.py      # Asyncio pub/sub ve IPC socket yönetimi
│   └── state.py          # Ring-buffer ve bellek yönetimi
│
├── ui/
│   ├── app.py            # Main Textual App ve Grid Layout
│   ├── panes/
│   │   ├── error_pane.py # Özellik 2: Error & Health Monitor
│   │   ├── sniper_pane.py# Özellik 3: Custom Log Sniper (Regex)
│   │   ├── minion_pane.py# Canlı ajan terminal pencereleri
│   │   └── plugin_pane.py# Özellik 7: Plugin Hub / Tool Manager
│   └── theme.py          # Minion Sarısı (#FFE135) ve ANSI stilleri
│
├── plugins/
│   ├── docling_tool.py   # Belge işleme aracı
│   └── pgvector_tool.py  # Vektör veritabanı senkronizasyonu
│
├── reports/              # Özellik 9: Dışa aktarılan oturum raporları (.md / .json)
└── main.py               # Başlangıç noktası (CLI Entrypoint)

```

---

## 5. Başlangıç Kod İskeleti (`main.py` ve `app.py` Örneği)

Aşağıdaki kod, bu devasa kalenin ana iskeletini Python ve Textual kütüphanesiyle başlatır:

```python
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, Input
from textual.containers import Horizontal, Vertical

class ErrorHealthPane(Static):
    """Özellik 2: Hata ve Sağlık Monitörü Penceresi"""
    def compose(self) -> ComposeResult:
        yield Static("🚨 ERROR & HEALTH MONITOR", classes="pane-title error-title")
        yield Log(id="error-log", classes="log-stream")

class LogSniperPane(Static):
    """Özellik 3: Regex Log Sniper Penceresi"""
    def compose(self) -> ComposeResult:
        yield Static("🔍 CUSTOM LOG SNIPER (Regex)", classes="pane-title sniper-title")
        yield Input(placeholder="Filter regex (e.g. [ERROR|429])...", id="sniper-input")
        yield Log(id="sniper-log", classes="log-stream")

class MinionFortressApp(App):
    CSS = """
    Screen {
        background: #121212;
    }
    .pane-title {
        background: #FFE135;
        color: #000000;
        text-style: bold;
        padding-left: 1;
    }
    .error-title { background: #FF4444; color: #FFFFFF; }
    .sniper-title { background: #FFD700; color: #000000; }
    
    .log-stream {
        height: 1fr;
        color: #00FF00;
        background: #1e1e1e;
        border: heavy #FFE135;
    }
    
    #repl-bar {
        dock: bottom;
        height: 1;
        background: #222222;
        color: #FFE135;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            # Sol Panel: İstatistikler ve Ajan Listesi
            yield Vertical(Static("📊 Fortress Roster & Stats", id="stats"), id="left-sidebar", width=35)
            
            # Sağ Panel: Sınırsız Bölünebilir Grid
            with Vertical(id="right-canvas"):
                with Horizontal():
                    yield ErrorHealthPane()
                    yield LogSniperPane()
        
        # Özellik 10: İnteraktif REPL Komut Satırı
        yield Input(placeholder="minion> Type command here (Press F12 for Banana Mode)...", id="repl-bar")
        yield Footer()

    async def on_mount(self) -> None:
        # Arka plan Daemon event loop simülasyonu
        error_log = self.query_one("#error-log", Log)
        error_log.write("[19:02:10] [INFO] Fortress initialized successfully.")
        error_log.write("[19:03:45] [WARN] RAM usage reached 82%.")

if __name__ == "__main__":
    app = MinionFortressApp()
    app.run()

```