# StockTracker Bot

Türk giyim mağazalarında (Zara, DeFacto…) tükenen ürünlerin belirli bir
**bedeni** tekrar stoğa girince Telegram üzerinden bildirim gönderen bot.

## Özellikler

- 🔗 Ürün linkini Telegram'a yapıştır, bot bedenleri ve stok durumunu (✅/❌) buton olarak gösterir.
- 🔔 Takip ettiğin beden stoğa girdiğinde tek seferlik bildirim alırsın (aynı stok için tekrar spam yok).
- 📋 `/liste` ile aktif takiplerini gör, tek dokunuşla sil.
- ⏱ Arka planda periyodik poller (varsayılan 10 dk) tüm abonelikleri kontrol eder.
- 💾 SQLite (varsayılan) veya herhangi bir SQLAlchemy destekli veritabanı (`DB_URL` ile).

## Desteklenen Mağazalar

| Mağaza | Durum | Yöntem |
|---|---|---|
| Zara | ✅ | `products-details` JSON ucu (tek istek) |
| DeFacto | ✅ | HTML'e gömülü `SizeName` / `StockQuantity` |
| Bershka / Pull & Bear | ❌ | Inditex Akamai — headless tarayıcıyı bile bloklıyor |
| LC Waikiki | ❌ | Akamai WAF — httpx 403, Playwright protokol hatası |
| H&M | ❌ | Akamai — httpx 403, Playwright "Access Denied" |

> ❌ işaretli mağazalar residential IP'de headless Playwright + stealth ile bile
> bloklandı. Güvenilir çekim için ücretli bir anti-bot servisi (unblocker/proxy)
> gerekir — küçük, ücretsiz barınan bir araç için orantısız bir maliyet.

---

## Yerel Geliştirme

### Gereksinimler

- Python 3.13+
- Telegram bot token ([@BotFather](https://t.me/BotFather) üzerinden ücretsiz)

### Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env içindeki TELEGRAM_BOT_TOKEN'ı BotFather'dan aldığın token ile doldur.
```

### Telegram Bot Token Alma

1. Telegram'da [@BotFather](https://t.me/BotFather)'a yaz.
2. `/newbot` → bota bir isim ve kullanıcı adı ver.
3. Verdiği token'ı `.env` dosyasındaki `TELEGRAM_BOT_TOKEN`'a yapıştır.

### Çalıştırma

```bash
python -m stock_tracker.bot.main
```

Sonra Telegram'da botuna `/start` yaz.

---

## Yapılandırma

Tüm ayarlar ortam değişkeni (`.env` veya deploy ortamının secret/variable
mekanizması) üzerinden okunur:

| Değişken | Zorunlu | Varsayılan | Açıklama |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | BotFather'dan alınan bot token'ı |
| `DB_URL` | ❌ | `sqlite:///stock_tracker.db` | SQLAlchemy bağlantı dizesi (üretimde `sqlite:////data/stock_tracker.db` veya `postgresql+psycopg://...`) |
| `POLL_INTERVAL_MINUTES` | ❌ | `10` | Stok kontrol sıklığı (dakika). Sitelere kibar olmak için 5'in altına inme. |

---

## Deploy — VPS (Önerilen)

Bot bir **worker** olarak long-polling ile çalışır — public port veya webhook gerekmez.
SQLite verisi `stock_tracker_data` adlı kalıcı bir Docker volume'de (`/data`) tutulur.

Aşağıdaki adımlar Ubuntu 22.04/24.04 tabanlı herhangi bir VPS için geçerlidir
(Oracle Cloud Always Free, Hetzner, DigitalOcean vb.).

### 1. Sunucuya SSH ile Bağlan

```bash
ssh kullanici@SUNUCU_IP
```

### 2. Repo'yu Klonla

```bash
sudo mkdir -p /opt/apps
sudo chown $USER:$USER /opt/apps
git clone https://github.com/seniih/stock-tracker-bot.git /opt/apps/stock_tracker
cd /opt/apps/stock_tracker
```

### 3. Botu Kur ve Başlat

`setup.sh` Docker'ı otomatik olarak kurar (yoksa), imajı build eder ve botu
`--restart unless-stopped` ile 7/24 ayakta tutar.

```bash
TELEGRAM_BOT_TOKEN=BURAYA_BOTFATHER_TOKEN bash deploy/setup.sh
```

Kurulum tamamlanınca aşağıdaki çıktıyı görmelisin:

```
==> Docker kuruluyor (gerekliyse)...
==> Imaj build ediliyor...
==> Eski konteyner varsa kaldiriliyor...
==> Bot baslatiliyor (7/24, otomatik yeniden baslatmali)...
Tamam! Loglari izle:   sudo docker logs -f stock-tracker
Durum:                 sudo docker ps
```

### 4. Kurulumu Doğrula

```bash
# Konteynerin ayakta olduğunu kontrol et
sudo docker ps

# Logları canlı izle (Ctrl+C ile çık)
sudo docker logs -f stock-tracker
```

`Bot başlatılıyor` satırını gördüysen bot çalışıyor demektir.

---

## Logları İzleme ve Yönetim

### Temel Log Komutları

```bash
# Logları canlı takip et
sudo docker logs -f stock-tracker

# Son 100 satırı göster
sudo docker logs --tail 100 stock-tracker

# Son 1 saatin loglarını göster
sudo docker logs --since 1h stock-tracker

# Belirli bir zaman aralığındaki logları göster
sudo docker logs --since "2025-01-01T00:00:00" --until "2025-01-01T23:59:59" stock-tracker
```

> **Not:** `setup.sh` konteyneri `--log-opt max-size=10m --log-opt max-file=3`
> ile başlatır. Bu sayede log dosyaları en fazla 3×10 MB = 30 MB yer kaplar,
> otomatik döndürülür.

### Konteyner Durumu ve Yönetim

```bash
# Çalışan konteynerleri listele
sudo docker ps

# Konteynerin kaynak kullanımını izle (CPU, RAM)
sudo docker stats stock-tracker

# Botu yeniden başlat
sudo docker restart stock-tracker

# Botu durdur
sudo docker stop stock-tracker

# Botu tekrar başlat
sudo docker start stock-tracker
```

### Güncelleme (Manuel)

Yeni bir sürüm yayınlandığında VPS'te şunu çalıştır:

```bash
cd /opt/apps/stock_tracker
git pull --ff-only
TELEGRAM_BOT_TOKEN=BURAYA_BOTFATHER_TOKEN bash deploy/setup.sh
```

`setup.sh` eski konteyneri kaldırıp yeni imajı build ederek botu günceller.
Volume (`/data`) silinmez, tüm abonelikler korunur.

---

## Otomatik Deploy (GitHub Actions)

`main` branch'ine her `git push`'ta `.github/workflows/deploy.yml` SSH ile VPS'e
bağlanıp `git pull` + `deploy/setup.sh` çalıştırır — manuel müdahale gerekmez.

### GitHub Secrets Kurulumu

Repo → **Settings → Secrets and variables → Actions → New repository secret**
ile aşağıdaki secret'ları ekle:

| Secret | Açıklama |
|---|---|
| `VPS_HOST` | Sunucunun IP adresi veya domain'i |
| `VPS_USER` | SSH kullanıcı adı (örn. `ubuntu`, `root`) |
| `VPS_SSH_KEY` | Deploy için üretilen SSH private key |
| `VPS_SSH_PORT` | SSH portu (opsiyonel, varsayılan `22`) |
| `TELEGRAM_BOT_TOKEN` | BotFather token'ı |

### Deploy SSH Anahtarı Oluşturma

```bash
# Lokal makinende yeni bir anahtar çifti üret (passphrase boş bırak)
ssh-keygen -t ed25519 -C "stock-tracker-deploy" -f ~/.ssh/stock_tracker_deploy

# Public key'i sunucuya ekle (sunucuda çalıştır)
cat ~/.ssh/stock_tracker_deploy.pub >> ~/.ssh/authorized_keys

# Private key'i kopyala → GitHub'da VPS_SSH_KEY secret'ına yapıştır
cat ~/.ssh/stock_tracker_deploy
```

### Otomatik Deploy Akışı

```
git push → GitHub Actions tetiklenir
         → SSH ile VPS'e bağlanır
         → git pull --ff-only
         → deploy/setup.sh çalışır (imaj rebuild + konteyner güncellenir)
         → Bot yeni sürümle ayağa kalkar
```

---

## Alternatif: Railway

1. Yeni proje → **"Deploy from GitHub repo"** (veya `railway up`). Dockerfile otomatik algılanır.
2. **Variables:** `TELEGRAM_BOT_TOKEN` = token, `DB_URL` = `sqlite:////data/stock_tracker.db`
3. **Volume** ekle, mount yolu `/data` (SQLite'ın kalıcı olması için).
4. Deploy → Logs'tan `Bot başlatılıyor` satırını gör.

> Alternatif: Volume yerine Railway Postgres eklentisi kullanıp `DB_URL`'i
> `postgresql+psycopg://...` yapabilirsin (bu durumda `psycopg[binary]` bağımlılığı eklenir).

---

## Proje Yapısı

```
stock_tracker/
  bot/
    main.py       # giriş noktası: Application kurulumu + poller zamanlayıcısı
    handlers.py   # Telegram komut/callback handler'ları
    keyboards.py  # inline klavye (beden seçimi, abonelik listesi)
  core/
    config.py     # .env'den ayar okuma
    db.py         # SQLAlchemy engine/session yönetimi
    models.py     # User / Product / Subscription tabloları
    repo.py       # veritabanı sorguları (handler'ları temiz tutar)
    poller.py     # periyodik stok kontrolü + bildirim
  adapters/
    base.py       # ortak StockAdapter arayüzü + registry
    zara.py       # Zara adaptörü
    defacto.py    # DeFacto adaptörü
    http.py       # paylaşılan, rate-limit'li HTTP istemcisi
deploy/
  setup.sh        # tek komutla VPS kurulum scripti
```

---

## Yol Haritası

- [x] Faz 0 — İskelet + `/start`
- [x] Faz 1 — İlk mağaza adaptörü: **Zara** (uçtan uca çalışıyor)
- [x] Faz 2 — Link gönder → bedenleri butonla seç → abone ol · `/liste` · sil
- [x] Faz 3 — Poller + bildirim (yok→var geçişinde haber, spam yok)
- [x] Faz 4 — DeFacto eklendi (Bershka/Pull&Bear/LCW/H&M: Akamai bloğu, bkz. yukarıdaki tablo)
- [x] Faz 5 — Deploy hazır (Dockerfile + `deploy/setup.sh`, VPS + GitHub Actions ile otomatik güncelleme)
