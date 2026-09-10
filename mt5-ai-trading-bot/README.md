# 🤖 MT5 Automation Trading

Bot trading otomatis untuk **MetaTrader 5** yang ditenagai AI (LLM). Bot membaca kondisi pasar dari chart & indikator, lalu AI memutuskan apakah akan **BUY / SELL / HOLD**, memasang **pending order**, atau **menutup posisi** — lengkap dengan manajemen risiko otomatis (risk-based lot sizing, SL/TP, break-even, trailing stop, partial TP).

Semua dikontrol dari **aplikasi desktop (GUI)** — tidak perlu menulis kode. Ada juga **menu Telegram** untuk memantau & mengontrol dari HP.

> ⚠️ **Untuk akun DEMO dulu.** Bot ini berhubungan langsung dengan uang (walau di akun demo). Pahami semua setting sebelum mencoba di akun real.

---

## 📑 Daftar Isi
1. [Fitur Utama](#-fitur-utama)
2. [Kebutuhan Sistem](#-kebutuhan-sistem)
3. [Instalasi / Persiapan Awal](#-instalasi--persiapan-awal)
4. [Cara Menjalankan](#-cara-menjalankan)
5. [Panduan Tab GUI (Semua Inputan)](#-panduan-tab-gui)
6. [Cara Kerja Bot](#-cara-kerja-bot)
7. [Menu & Perintah Telegram](#-menu--perintah-telegram)
8. [Strategi & Jenis Order](#-strategi--jenis-order)
9. [Pemecahan Masalah (Troubleshooting)](#-pemecahan-masalah)
10. [Struktur Proyek](#-struktur-proyek)
11. [Keterbatasan & Catatan Penting](#-keterbatasan--catatan-penting)

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 🧠 **Keputusan oleh AI** | AI melihat data harga + indikator (EMA, RSI, MACD, Stochastic) + **gambar chart** (vision), lalu memberi keputusan lengkap dengan alasan |
| 📊 **Multi-pair & multi-timeframe** | Scan beberapa pair sekaligus; tiap pair bisa punya timeframe sendiri |
| ⚖️ **Risk management otomatis** | Ukuran lot dihitung dari risiko (% balance), minimal RR 1:1.5, batas SL/TP, filter spread |
| 📈 **Trade management** | Break-even (BE), trailing stop, partial TP — posisi yang sudah profit dikelola otomatis |
| 📱 **Telegram** | Menu tombol: Status, PnL, Posisi, Sinyal, Setting, Pilih Pair, Stop — dari HP |
| 🖥 **GUI lengkap** | Semua setting bisa diubah lewat form; ada terminal log, tombol test koneksi, auto-detect MT5 |
| 🔄 **Hot-reload** | Simpan setting dari GUI → langsung berlaku di scan berikutnya, tanpa restart bot |
| 🔌 **Auto-detect** | Deteksi otomatis path MT5 & nama pair asli broker (beda broker beda penamaan: `XAUUSD.v`, `XAUUSDm`, dll) |

---

## 💻 Kebutuhan Sistem

- **Windows 10/11**
- **MetaTrader 5** terpasang & **sudah login** ke akun (disarankan akun **demo** dulu)
- **AutoTrading aktif** di MT5 (tombol **Algo Trading** di toolbar — harus hijau)
- Koneksi internet (untuk panggil AI)
- Satu dari dua cara jalan:
  - **Aplikasi jadi**: `Automation Trading.exe` (tidak perlu install Python)
  - **Dari source**: Python 3.10+ dengan package di `requirements.txt`

> Untuk akun **Vantage** (contoh yang dipakai saat pengembangan): pasang MetaTrader 5 Vantage, login akun demo. Path terminal biasanya `C:\Program Files\MetaTrader 5\terminal64.exe`.

---

## 🔧 Instalasi / Persiapan Awal

### Opsi A — Pakai aplikasi jadi (EXE)
1. Copy folder proyek (berisi `Automation Trading.exe`, `config.yaml`, folder `assets/`, `logs/`) ke komputer.
2. Jalankan `Automation Trading.exe`.
3. Lanjut ke [Cara Menjalankan](#-cara-menjalankan).

### Opsi B — Jalankan dari source (untuk developer)
```bash
# 1. buat virtual environment & install dependensi
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt        # MetaTrader5, yaml, numpy, pandas, matplotlib, requests, openai

# 2. jalankan GUI
python gui_app.py
```

> Jika `python` tidak dikenali, pakai `py` atau path lengkap Python Anda.

### Menyiapkan MT5
1. Buka MT5, login ke akun (**demo**).
2. Klik tombol **Algo Trading** di toolbar sampai berwarna **hijau** (AutoTrading ON).
3. Biarkan MT5 tetap terbuka selama bot jalan.
4. (Opsional) di tab **Koneksi** GUI, klik **🔍 Deteksi Otomatis** — path MT5 dan nama pair broker terisi otomatis.

### Menyiapkan AI (9Router / OpenAI-compatible API)
Bot butuh server API yang kompatibel dengan OpenAI. Contoh: **9Router** di `http://localhost:20128/v1`.
- **Base URL**: `http://localhost:20128/v1`
- **API Key**: isi key 9Router Anda (di GUI: tab **🔌 Koneksi** → field *API Key (9Router)*)
- **Model**: `COMBO` (disarankan) atau model spesifik lain

---

## ▶️ Cara Menjalankan

1. **Buka MT5** → pastikan sudah login & AutoTrading **hijau**.
2. **Jalankan `Automation Trading.exe`**.
3. Di tab **🔌 Koneksi**: isi/verifikasi *MT5 Terminal Path*, *9Router URL*, *API Key*, *Model*.
4. Klik tombol test satu per satu (pastikan semua sukses):
   - **🔌 Test 9Router** → koneksi ke server AI OK
   - **🏛 Test MT5** → MT5 terhubung, akun & saldo muncul
   - **📱 Test Telegram** → bot Telegram kirim pesan uji (opsional)
5. Atur pair yang ingin di-scan di tab **📊 Symbol & TF** (lihat panduan tab).
6. Klik **💾 Simpan Config** (atau langsung **▶ Start Bot** — otomatis tersimpan).
7. Klik **▶ Start Bot**. Status berubah jadi **🟢 RUNNING**, terminal log menampilkan scan tiap interval (default 60 detik):
   ```
   🔍 Scan dimulai: XAUUSD, EURUSD, GBPUSD, NAS100.r
      • Fetch data XAUUSD …
      • XAUUSD: 500 baris data siap
      • XAUUSD AI: HOLD conf=0.42 reason=…
   ```
8. Untuk menghentikan: klik **■ Stop Bot**.

> 💡 Bot membaca semua pasangan yang dicentang di **"Pair aktif di-scan"**. Bagian **"Pair yang diizinkan (universe)"** hanya daftar kandidat. Kosongkan semua centang subset = scan **semua** universe.

---

## 📖 Panduan Tab GUI (Semua Inputan)

Aplikasi punya 8 tab. Berikut penjelasan **setiap field**.

### 🖥 Terminal
Log berjalan bot secara real-time — tempat melihat bot sedang melakukan apa.
- **🗑 Bersihkan** — hapus isi log
- **📋 Salin Semua** — salin seluruh log ke clipboard (untuk laporan error)

### 🔌 Koneksi
| Field | Keterangan | Contoh |
|---|---|---|
| **MT5 Terminal Path** | Lokasi `terminal64.exe` | `C:/Program Files/MetaTrader 5/terminal64.exe` |
| **9Router URL** | Base URL server AI | `http://localhost:20128/v1` |
| **API Key (9Router)** | API key server AI | `sk-…` |
| **API Key Env Var** | (Opsional) nama env var sebagai cadangan | `MY_API_KEY` |
| **Model AI** | Model yang dipakai AI | `COMBO` (disarankan) |
| **Strategi** | Strategi analisis | `adaptive` (disarankan) |
| **Custom Prompt File** | File teks berisi instruksi khusus (kosongkan = default) | `custom.txt` |
| **Temperature** | Kreativitas AI (rendah = konsisten) | `0.1` |
| **Timeout (detik)** | Batas waktu panggilan AI | `120` |
| **Max Tokens** | Panjang maksimal jawaban AI | `4096` |

**Vision (AI melihat gambar chart):**
| Field | Keterangan |
|---|---|
| **Aktif** | Aktifkan AI melihat gambar chart + data angka |
| **Jumlah Candle** | Berapa candle terakhir digambar | `120` |
| **Chart TF** | Timeframe chart yang digambar | `M5` |
| **Lebar/Tinggi px** | Resolusi gambar | `1400×800` |
| **Overlay indikator** | Gambar EMA/BB di atas chart |

**Lainnya:**
- **🔍 Deteksi Otomatis** — isi path MT5 + nama-nama pair broker secara otomatis
- **Scan Interval (detik)** — jeda antar scan | `60`

### 📊 Symbol & TF
| Bagian | Keterangan |
|---|---|
| **Pair yang diizinkan (universe)** | Daftar pair yang *boleh* dipakai (kandidat). Centang pair broker Anda. |
| **Pair tambahan** | Pair di luar daftar (tulis manual, pisah koma) — mis. pair dengan suffix broker seperti `NAS100.r` |
| **Pair aktif di-scan (subset)** | Pair yang **benar-benar di-scan** tiap siklus. **Kosong = semua universe.** Ini yang menentukan bot scan apa. |
| **Timeframes analisis** | Timeframe yang dikirim ke AI | `M5 M15 M30 H1 H4` |
| **Default TF** | TF default untuk pair tanpa override | `M5, M15, H1` |
| **XAUUSD override TF** | TF khusus untuk XAUUSD (mis. perlu konfirmasi big-TF) | centang sesuai |
| **Mode (data)** | `compact` = ringkas (hemat token) / `full` = semua baris | `compact` |
| **Tail N candle / Tail TF** | Berapa candle terakhir yang dikirim | `40` / `M5` |

### ⚖️ Risk
| Field | Keterangan | Contoh |
|---|---|---|
| **Mode Lot** | `auto` = hitung dari risiko, `fixed` = lot tetap, `manual` = lot manual | `auto` |
| **Risk %** | Risiko per trade dari balance (mode auto) | `1.0` (%) |
| **Fixed Lots** | Lot tetap (mode fixed) | `0.01` |
| **Manual Lot** | Lot manual (mode manual) | `0.01` |
| **Min Confidence** | Skor keyakinan AI minimal untuk entry | `0.55` |
| **Max Spread (points)** | Spread maksimal yang ditoleransi | `50` |
| **Cooldown (menit)** | Jeda antar order per pair setelah order | `3` |
| **Min RR** | Risk:Reward minimal | `1.5` |
| **Max Lots/Trade** | Batas lot per order | `0.5` |
| **Min SL (points)** | Jarak SL minimal (anti SL terlalu dekat) | `10` |
| **Max Open Posisi/Pair** | Maksimal posisi per pair | `5` |
| **Max Correlated Posisi** | Batas posisi pair yang berkorelasi | `2` |
| **Daily Loss Halt (%)** | Hentikan trading hari itu jika loss harian mencapai % ini | `5.0` |
| **Time Filter** | Blokir trading di jam tertentu (timezone Asia/Jakarta) | kosong |

### 🎯 Per-Pair (RR & Spread)
Grid pengaturan **per pair** (mengalahkan setting global):
- **RR min** & **target pips min/max** — target profit per pair (mis. XAUUSD 70–250 pips, NAS100.r 150–500)
- **Max spread override** — `unlimited` untuk pair ber-spread lebar (contoh: NAS100.r)
- **Max jarak pending** — override jarak pending order

> ⚠️ Nama pair di sini harus sama dengan **base name** broker Anda (mis. tulis `XAUUSD`, bukan `XAUUSD.v`) supaya tetap cocok saat pindah broker.

### 📱 Telegram
| Field | Keterangan |
|---|---|
| **Aktifkan Telegram** | Nyalakan notifikasi & kontrol via bot Telegram |
| **Bot Token** | Token dari @BotFather | `8568932671:…` |
| **Chat ID** | ID chat/telegram Anda | `895862325` |
| **Token/Chat ID Env Var** | (Opsional) nama env var pengganti |
| **Kirim chart saat ada sinyal** | Bot kirim **gambar chart** + alasan tiap ada sinyal (bukan HOLD) |
| **Symbols chart** | Pair mana yang chart-nya dikirim (kosong = semua) | `XAUUSD` |

Cara membuat bot Telegram:
1. Di Telegram, chat ke **@BotFather** → `/newbot` → ikuti petunjuk → dapat **token**.
2. Untuk **chat ID**: chat ke bot Anda, lalu buka `https://api.telegram.org/bot<TOKEN>/getUpdates` di browser — cari angka `"chat":{"id":…}`.
3. Masukkan keduanya di GUI, klik **📱 Test Telegram**.

### 📈 Trade Mgmt
Manajemen posisi yang sudah terbuka (diperiksa tiap scan):
| Field | Keterangan | Contoh |
|---|---|---|
| **Aktifkan trade management** | Master switch | ✅ |
| **Gunakan BE (break-even)** | Geser SL ke harga masuk saat profit cukup | ✅ |
| **BE Agresif** | BE lebih awal (trigger kecil) | ✅ |
| **BE Trigger (points)** | Profit berapa SL digeser ke BE | `30` |
| **BE Lock (points)** | Lock profit minimal setelah BE | `5` |
| **Gunakan trailing** | SL mengikuti harga saat profit naik | ✅ |
| **Trailing Start (points)** | Profit minimal sebelum trailing aktif | `100` |
| **Trailing Step (points)** | Jarak langkah trailing | `20` |
| **Aktifkan partial TP** | Tutup sebagian posisi saat profit tertentu | ✅ |
| **Trigger fraksi** | Profit (fraksi dari jarak TP) untuk memicu partial | `0.6` |
| **Close fraksi** | Berapa bagian posisi ditutup | `0.5` (50%) |
| **AI evaluasi posisi** | AI ikut menilai posisi terbuka secara berkala | ✅ |
| **Interval evaluasi (menit)** | Seberapa sering | `15` |

### ⚙️ Advanced
| Field | Keterangan | Contoh |
|---|---|---|
| **Magic Number** | Penanda order bot (jangan sama dengan bot lain) | `20250903` |
| **Slippage (points)** | Toleransi selisih harga saat eksekusi | `20` |
| **Pending Max Dist (points)** | Jarak maksimal pending dari harga saat ini | `5000` |
| **Min/Max SL (points)** | Batas jarak SL | `10` / `20000` |
| **Min/Max TP (points)** | Batas jarak TP | `10` / `40000` |
| **Allowed order types** | Centang: `market` &/atau `pending` |
| **Timezone / Block ranges** | Jam larangan trading | `Asia/Jakarta` / kosong |
| **Host / Port / API Key Env** | Untuk mode server (opsional, jarang dipakai) | `127.0.0.1` / `8790` |

### Tombol Kontrol Utama (di atas, selalu terlihat)
- **▶ Start Bot** — simpan config lalu mulai loop scan
- **■ Stop Bot** — hentikan bot (pending order **tidak** otomatis dicancel; posisi terbuka dibiarkan)
- **🔌 Test 9Router** / **🏛 Test MT5** / **📱 Test Telegram** — tes koneksi
- **Status** — `⏸ STOPPED` / `🟢 RUNNING` / dll

---

## 🔄 Cara Kerja Bot

Satu siklus (default tiap **60 detik**):

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ 1. Ambil    │→  │ 2. AI        │→  │ 3. Risk     │→  │ 4. Eksekusi  │
│ data MT5    │   │ menganalisis │   │ Guard cek   │   │ order + TM   │
│ (OHLCV+chart)│   │ semua pair   │   │ RR/spread/dll│   │              │
└─────────────┘   └──────────────┘   └─────────────┘   └──────────────┘
```

1. **Ambil data** — untuk tiap pair aktif: candle dari semua timeframe terpilih + indikator (EMA20/50, RSI14, MACD, Stochastic) + gambar chart (bila vision aktif).
2. **AI menganalisis** — semua pair diproses **paralel**. AI mengembalikan JSON: `decision`, `entry`, `sl`, `tp`, `pending_price`, `confidence`, `reason`. Jika HOLD → tidak ada order (pending lama yang basi ikut dicancel).
3. **Risk Guard** — sebelum eksekusi dipastikan: confidence ≥ minimum, RR ≥ minimum, spread wajar, jarak SL ≥ minimum, belum kena daily-loss halt, tidak overload posisi. **Jika tidak lolos → order diblokir dengan alasan.**
4. **Eksekusi** — market order langsung masuk, atau pending order dipasang. Ukuran lot dari risk % balance. Setelah itu trade management (BE/trailing/partial TP) menjaga posisi. Notifikasi dikirim ke Telegram.

Keputusan AI tiap scan dicatat (riwayat sinyal, maks 50) & bisa dilihat via Telegram **🧠 Sinyal**.

---

## 📱 Menu & Perintah Telegram

Setelah Telegram aktif & bot jalan, buka chat bot Anda. Ada **tombol menu** (reply keyboard) & bisa juga ketik perintah:

| Perintah / Tombol | Fungsi |
|---|---|
| `📊 Status` / `/status` | Status bot, koneksi MT5, akun, balance, spread |
| `📈 PnL` / `/pnl` | PnL hari ini, balance awal hari, posisi terbuka, pending |
| `📌 Posisi` / `/posisi` | Daftar posisi terbuka (symbol, arah, lot, harga, SL/TP, profit) |
| `🧠 Sinyal` / `/sinyal` | Riwayat sinyal AI terakhir |
| `⚙️ Setting` / `/setting` | Ringkasan setting aktif |
| `🎯 Pilih Pair` / `/pilihpair` | Pilih pair yang di-scan langsung dari HP (inline tombol) |
| `🔢 Lot` / `/lot <angka>` | Ubah lot (mode manual) — contoh: `/lot 0.05` |
| `📋 Menu` / `/menu` | Tampilkan menu inline |
| `ℹ️ Bantuan` / `/bantuan` | Daftar perintah |
| `🛑 Stop Bot` / `/stop` | **Hentikan bot** dari HP |

Bot juga **mengirim notifikasi** otomatis: order masuk/gagal/diblokir, posisi ditutup, laporan PnL berkala (~30 menit), dan gambar chart saat ada sinyal (jika diaktifkan).

---

## 📈 Strategi & Jenis Order

### Strategi (`adaptive` disarankan)
AI memilih pendekatan sesuai kondisi pasar dari beberapa kerangka:
- **SMC** — Order Block, Fair Value Gap, Breaker, Liquidity Sweep, BOS/CHoCH
- **ICT** — Displacement, MSS, Killzone, Premium/Discount
- **Supply & Demand**, **Trend Following**, **Breakout**, **Scalping**

### Jenis order yang bisa dipasang AI
| Keputusan AI | Arti |
|---|---|
| `BUY` / `SELL` | Market order langsung |
| `BUY_LIMIT` | Beli saat harga **turun** ke level tertentu |
| `SELL_LIMIT` | Jual saat harga **naik** ke level tertentu |
| `BUY_STOP` | Beli saat harga **naik** menembus level |
| `SELL_STOP` | Jual saat harga **turun** menembus level |
| `HOLD` | Tidak melakukan apa-apa (pending yang basi dicancel) |
| `CLOSE` | Tutup posisi |

### Target per pair (default)
| Pair | RR min | Target (pips) |
|---|---|---|
| XAUUSD | 1:1.5 | 70–250 |
| NAS100.r | 1:2.0 | 150–500 |
| EURUSD / GBPUSD / USDJPY | 1:1.5 | 40–150 |
| AUDUSD | 1:1.5 | 35–140 |

---

## 🔧 Pemecahan Masalah

| Gejala | Penyebab & Solusi |
|---|---|
| `❌ FATAL: tidak bisa konek MT5` | MT5 belum terbuka / belum login. Cek path terminal di tab Koneksi (klik **🔍 Deteksi Otomatis**), pastikan MT5 jalan. |
| Order ditolak `AutoTrading disabled` | Klik tombol **Algo Trading** di MT5 sampai **hijau**. |
| Bot tidak scan pair yang saya mau | Centang pair di **"Pair aktif di-scan (subset)"** (bukan hanya universe) → **Simpan** → **Start Bot**. Setelah bot jalan, Simpan langsung berlaku di scan berikutnya (tanpa restart). |
| `ORDER FAIL … (-2, 'Unnamed arguments not allowed')` | Bug lama yang sudah diperbaiki — pastikan pakai versi EXE terbaru. |
| AI tidak menjawab / timeout | Cek 9Router/API server jalan (`Test 9Router`), API key benar, model valid. |
| Telegram tidak ada notifikasi | `Test Telegram` gagal → cek token & chat ID. Token harus dari @BotFather (format `123456:…`). |
| Pair tidak ketemu (`symbol not found`) | Nama pair broker beda. Klik **🔍 Deteksi Otomatis** untuk ambil nama asli, atau tulis di **Pair tambahan** (contoh `NAS100.r`). |
| Spread terlalu lebar → semua diblokir | Pair indeks seperti NAS100.r perlu override `unlimited` di tab **Per-Pair**. |
| EXE tidak bisa di-replace saat build | Proses EXE lama masih jalan. Tutup dulu (Task Manager), baru build. |
| Config bermasalah setelah edit manual | Bot otomatis backup ke `config.yaml.bak` saat menyimpan. Kembalikan backup jika perlu. |

---

## 🗂 Struktur Proyek

```
mt5-ai-trading-bot/
├── Automation Trading.exe    # Aplikasi jadi (double-click untuk jalan)
├── gui_app.py                # GUI utama (semua kontrol)
├── config.yaml               # Semua setting (diedit lewat GUI)
├── config.yaml.bak           # Backup config otomatis
├── .active_pairs.json        # Pair aktif (dikelola GUI/Telegram)
├── run_bot.py                # Entry point tanpa GUI (CLI: --once / --loop 60)
├── ui_smoke_test.py          # Tes otomatis GUI
├── assets/                   # Ikon & logo
├── logs/                     # engine.log (rotating)
├── server/
│   ├── config.py             # Loader config (dotted-path)
│   ├── mt5_gateway.py        # Koneksi MT5, data, order, manajemen posisi
│   ├── engine.py             # Loop utama: scan → AI → risk → eksekusi
│   ├── ai/agent.py           # Pemanggil LLM (build context, parse keputusan)
│   ├── ai/prompts.py         # Template prompt strategi
│   ├── ai/chart_renderer.py  # Gambar chart untuk vision AI
│   ├── risk_guard.py         # Validasi sebelum eksekusi (RR, spread, dll)
│   ├── trade_manager.py      # Break-even, trailing, partial TP
│   ├── notifier.py           # Notifikasi & menu Telegram
│   └── logger_setup.py       # Konfigurasi log
├── backtest/                 # Backtest replay historis + AI
└── build/                    # File build PyInstaller
```

### CLI (tanpa GUI, untuk developer)
```bash
python run_bot.py --once        # scan satu kali lalu keluar
python run_bot.py --loop 60     # scan terus tiap 60 detik
```

---

## ⚠️ Keterbatasan & Catatan Penting

1. **Bukan saran keuangan.** Bot alat bantu; keputusan akhir tetap di tangan pengguna. Gunakan akun demo sampai paham & yakin.
2. **AI bisa salah.** Keputusan dari model bahasa — selalu ada kemungkinan sinyal tidak akurat. Risk Guard membantu membatasi, tapi tidak menjamin profit.
3. **MT5 harus tetap terbuka** selama bot jalan, dengan AutoTrading ON.
4. **Interval scan & responsivitas**: default 60 detik; AI bisa butuh waktu lebih lama untuk banyak pair — log menunjukkan progres.
5. **Posisi & pending saat bot berhenti**: bot berhenti tidak otomatis menutup posisi atau mencabut pending (aman — tidak ada aksi mendadak). Kelola manual jika perlu.
6. **Satu bot per akun**: jangan jalankan dua bot dengan *Magic Number* sama pada akun yang sama.
7. **Token Telegram bersifat rahasia** — jangan bagikan; bot lain bisa mengontrol bot Anda jika token bocor.
8. **File config** bisa diedit manual (format YAML) tapi disarankan lewat GUI agar tidak salah format. Bot otomatis membuat `config.yaml.bak` sebelum menimpa.

---

Selamat mencoba! 🚀 Mulai dari akun demo, pasang 1–2 pair dulu (mis. XAUUSD + EURUSD), dan pantau lewat tab **🖥 Terminal** serta Telegram.
