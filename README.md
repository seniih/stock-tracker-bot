# StockTracker

Türk giyim mağazalarında (Zara, DeFacto…) tükenen ürünlerin belirli bir
**bedeni** tekrar stoğa girince Telegram üzerinden bildirim gönderen bot.

## Özellikler

- 🔗 Ürün linkini Telegram'a yapıştır, bot bedenleri ve stok durumunu (✅/❌) buton olarak gösterir.
- 🔔 Takip ettiğin beden stoğa girdiğinde tek seferlik bildirim alırsın (aynı stok için tekrar spam yok).
- 📋 `/liste` ile aktif takiplerini gör, tek dokunuşla sil.
- ⏱ Arka planda periyodik poller (varsayılan 10 dk) tüm abonelikleri kontrol eder.
- 💾 SQLite (varsayılan) veya herhangi bir SQLAlchemy destekli veritabanı (`DB_URL` ile).

## Desteklenen mağazalar

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

## Gereksinimler

- Python 3.13+
- Telegram bot token ([@BotFather](https://t.me/BotFather) üzerinden ücretsiz)

## Kurulum (yerel geliştirme)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env içindeki TELEGRAM_BOT_TOKEN'ı BotFather'dan aldığın token ile doldur.
```

### Telegram bot token'ı alma
1. Telegram'da [@BotFather](https://t.me/BotFather)'a yaz.
2. `/newbot` → bota bir isim ve kullanıcı adı ver.
3. Verdiği token'ı `.env` dosyasındaki `TELEGRAM_BOT_TOKEN`'a yapıştır.

## Yapılandırma

Tüm ayarlar ortam değişkeni (`.env` veya deploy ortamının secret/variable
mekanizması) üzerinden okunur:

| Değişken | Zorunlu | Varsayılan | Açıklama |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | BotFather'dan alınan bot token'ı |
| `DB_URL` | ❌ | `sqlite:///stock_tracker.db` | SQLAlchemy bağlantı dizesi (üretimde `sqlite:////data/stock_tracker.db` veya `postgresql+psycopg://...`) |
| `POLL_INTERVAL_MINUTES` | ❌ | `10` | Stok kontrol sıklığı (dakika). Sitelere kibar olmak için 5'in altına inme. |

## Çalıştırma

```bash
python -m stock_tracker.bot.main
```

Sonra Telegram'da botuna `/start` yaz.

## Proje yapısı

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
```

## Deploy (7/24 bulut)

Bot bir **worker** olarak long-polling ile çalışır — public port/webhook gerekmez.
SQLite verisi kalıcı bir diskte (`/data`) tutulur.

### Kendi VPS'in (önerilen)

Tek komutla kurulum: Docker'ı kurar, imajı build eder ve botu
`--restart unless-stopped` ile 7/24 ayakta tutar. SQLite verisi
`stock_tracker_data` adlı kalıcı bir Docker volume'de (`/data`) tutulur.

**İlk kurulum (Ubuntu VM, SSH ile bağlanıp):**
```bash
git clone https://github.com/seniih/stock-tracker-bot.git /opt/stock_tracker
cd /opt/stock_tracker
TELEGRAM_BOT_TOKEN=BURAYA_BOTFATHER_TOKEN bash deploy/setup.sh
sudo docker logs -f stock-tracker   # "Bot başlatılıyor" satırını gör
```

**Otomatik deploy (GitHub Actions):** `main`'e her `git push`'ta
`.github/workflows/deploy.yml` SSH ile VPS'e bağlanıp `git pull` +
`deploy/setup.sh` çalıştırır ve konteyneri günceller. Repo secrets'a
şunları ekle (Settings → Secrets and variables → Actions):

| Secret | Açıklama |
|---|---|
| `VPS_HOST` | Sunucunun IP adresi veya domain'i |
| `VPS_USER` | SSH kullanıcı adı (örn. `ubuntu`, `root`) |
| `VPS_SSH_KEY` | Deploy için üretilen SSH private key (public key'i sunucudaki `~/.ssh/authorized_keys`'e eklenmeli) |
| `VPS_SSH_PORT` | SSH portu (opsiyonel, varsayılan 22) |
| `TELEGRAM_BOT_TOKEN` | BotFather token'ı |

### Railway
1. Yeni proje → "Deploy from GitHub repo" (veya `railway up`). Dockerfile otomatik algılanır.
2. **Variables:** `TELEGRAM_BOT_TOKEN` = token, `DB_URL` = `sqlite:////data/stock_tracker.db`
3. **Volume** ekle, mount yolu `/data` (SQLite'ın kalıcı olması için).
4. Deploy → Logs'tan "Bot başlatılıyor" satırını gör.

> Alternatif: Volume yerine Railway Postgres eklentisi kullanıp `DB_URL`'i
> `postgresql+psycopg://...` yapabilirsin (bu durumda `psycopg[binary]` bağımlılığı eklenir).

## Yol haritası

- [x] Faz 0 — İskelet + `/start`
- [x] Faz 1 — İlk mağaza adaptörü: **Zara** (uçtan uca çalışıyor)
- [x] Faz 2 — Link gönder → bedenleri butonla seç → abone ol · `/liste` · sil
- [x] Faz 3 — Poller + bildirim (yok→var geçişinde haber, spam yok)
- [x] Faz 4 — DeFacto eklendi (Bershka/Pull&Bear/LCW/H&M: Akamai bloğu, bkz. yukarıdaki tablo)
- [x] Faz 5 — Deploy hazır (Dockerfile + `deploy/setup.sh`, VPS + GitHub Actions ile otomatik güncelleme)
