# StockTracker

Türk giyim mağazalarında (Zara, LC Waikiki, DeFacto, Bershka…) tükenen ürünlerin
belirli bir **bedeni** tekrar stoğa girince Telegram'dan bildirim gönderen bot.

## Kurulum (yerel)

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

## Çalıştırma

```bash
python -m stock_tracker.bot.main
```

Sonra Telegram'da botuna `/start` yaz.

## Proje yapısı

```
stock_tracker/
  bot/      # Telegram bot (komutlar, arayüz)
  core/     # config, veritabanı, modeller, poller
  adapters/ # her mağaza için stok çekme adaptörü
```

## Durum

- [x] Faz 0 — İskelet + `/start`
- [x] Faz 1 — İlk mağaza adaptörü: **Zara** (uçtan uca çalışıyor)
- [x] Faz 2 — Link gönder → bedenleri butonla seç → abone ol · `/liste` · sil
- [x] Faz 3 — Poller + bildirim (yok→var geçişinde haber, spam yok)
- [x] Faz 4 — DeFacto eklendi ✅ (Bershka/Pull&Bear/LCW/H&M: Akamai bloğu, bkz. tablo)
- [x] Faz 5 — Deploy hazır (Dockerfile + fly.toml, imaj doğrulandı)

### Desteklenen mağazalar
| Mağaza | Durum | Yöntem |
|---|---|---|
| Zara | ✅ | `products-details` JSON (tek istek) |
| DeFacto | ✅ | HTML gömülü `SizeName/StockQuantity` |
| Bershka / Pull & Bear | ❌ | Inditex Akamai — headless tarayıcıyı bile bloklıyor |
| LC Waikiki | ❌ | Akamai WAF — httpx 403, Playwright protokol hatası |
| H&M | ❌ | Akamai — httpx 403, Playwright "Access Denied" |

> Not: ❌ mağazalar residential IP'de headless Playwright + stealth ile bile
> bloklandı. Güvenilir çekim için ücretli anti-bot servisi (unblocker/proxy)
> gerekir — birkaç arkadaşlık ücretsiz barınan bir araç için orantısız.

## Deploy (7/24 bulut)

Bot bir **worker** olarak long-polling ile çalışır — public port/webhook gerekmez.
SQLite verisi kalıcı bir diskte (`/data`) tutulur.

### Fly.io (önerilen)
```bash
fly launch --no-deploy                                   # fly.toml'u kullanır
fly volume create stock_tracker_data --size 1 --region fra
fly secrets set TELEGRAM_BOT_TOKEN=BURAYA_BOTFATHER_TOKEN
fly deploy
fly logs                                                 # çalışıyor mu izle
```

### Railway
1. Yeni proje → "Deploy from GitHub repo" (veya `railway up`). Dockerfile otomatik algılanır.
2. **Variables:** `TELEGRAM_BOT_TOKEN` = token, `DB_URL` = `sqlite:////data/stock_tracker.db`
3. **Volume** ekle, mount yolu `/data` (SQLite'ın kalıcı olması için).
4. Deploy → Logs'tan "Bot başlatılıyor" satırını gör.

> Alternatif: Volume yerine Railway Postgres eklentisi kullanıp `DB_URL`'i
> `postgresql+psycopg://...` yapabilirsin (bu durumda `psycopg[binary]` bağımlılığı eklenir).

### Docker (yerel/kendi sunucun)
```bash
docker build -t stock_tracker .
docker run -d --name stock_tracker --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=BURAYA_TOKEN \
  -v stock_tracker_data:/data \
  stock_tracker
```
