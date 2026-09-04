# 📊 Automation Trading Suite

Kumpulan tools trading otomatis pribadi — **satu repository, dua proyek** yang saling terhubung:

| Proyek | Fungsi | Teknologi |
|---|---|---|
| [`mt5-ai-trading-bot/`](./mt5-ai-trading-bot/README.md) | Bot trading AI untuk MetaTrader 5 (scan → sinyal AI → eksekusi order → manajemen posisi), dikontrol lewat GUI desktop + Telegram | Python, MetaTrader5, PyInstaller |
| [`trading-journal/`](./trading-journal/README.md) | Web jurnal trading — catat otomatis semua transaksi dari MT5, lihat riwayat & statistik | Next.js 16, SQLite, Drizzle |

## 🔗 Cara Kerja Keduanya

```
MetaTrader 5 (terminal64.exe)
        │
        ▼
mt5-ai-trading-bot ──(mt5_sync.py, tiap interval)──► trading-journal (web :8500)
   (scan & eksekusi)                                        │
        │                                                    ▼
        ▼                                              database SQLite
   Telegram bot (@signaleav2bot)                    (data/journal.db)
```

- **Bot AI** menghasilkan sinyal & eksekusi order di MT5.
- **`mt5_sync.py`** (di folder bot) membaca posisi/riwayat dari MT5 dan mengirim ke web journal.
- **Journal** menyimpan semua trade + menampilkan statistik (waktu WIB), bisa diaktifkan auto-sync tiap N detik dari halaman Pengaturan.

## 🚀 Quick Start

### 1. Bot AI (`mt5-ai-trading-bot`)
1. Buka MT5 (login akun demo, **Algo Trading ON**).
2. Jalankan `AI Trading Bot.exe` (atau `python gui_app.py`).
3. Tab **Koneksi** → isi 9Router URL/API key/Model → **Test MT5** & **Test 9Router**.
4. Centang pair di **Symbol & TF** → **▶ Start Bot**.
5. Detail lengkap: [`mt5-ai-trading-bot/README.md`](./mt5-ai-trading-bot/README.md)

### 2. Web Journal (`trading-journal`)
1. `cd trading-journal && npm install && npm run build`
2. Salin `.env.example` → `.env`, isi path `MT5_SYNC_SCRIPT` (arah ke `mt5_sync.py` di folder bot).
3. `npm start -- -p 8500` → buka `http://127.0.0.1:8500`.
4. Di halaman **Pengaturan**, aktifkan **Auto Sync** (interval detik; 0 = manual).
5. Ada `setup.bat` untuk device baru — otomatis tanya path, install dependensi, dan build.

## 📁 Struktur Repository

```
AutomationTrading/
├── mt5-ai-trading-bot/     # Python bot (GUI + Telegram + AI)
│   ├── gui_app.py          # GUI desktop (8 tab)
│   ├── server/             # engine, mt5_gateway, ai/, risk_guard, notifier
│   ├── mt5_sync.py         # jembatan sync → trading-journal
│   └── build_exe.bat       # build exe (PyInstaller)
├── trading-journal/        # Next.js web jurnal
│   ├── src/                # app router, lib (sync, config)
│   ├── scripts/            # push-schema, run_mt5_sync
│   └── setup.bat           # setup device baru
└── .gitignore              # exe, .env, db, build cache — tidak di-push
```

## 🔒 Keamanan

- `config.yaml` (berisi API key & data akun MT5) → **tidak di-push**.
- `.env` (berisi token & path lokal) → **tidak di-push**; hanya `.env.example` yang ikut.
- Database journal (`data/journal.db`) → **tidak di-push**.
- `AI Trading Bot.exe` (65 MB, build artifact) → **tidak di-push** (bisa di-upload sebagai GitHub Release).

## ⚙️ Requirements

- Windows 10/11, MetaTrader 5 (login + AutoTrading)
- Python 3.10+ (`requirements.txt` di folder bot)
- Node.js 18+ & pnpm/npm (`package.json` di folder journal)
- Server API OpenAI-compatible (contoh: 9Router `http://localhost:20128/v1`)
