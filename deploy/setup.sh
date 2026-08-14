#!/usr/bin/env bash
# StockTracker'ı bir Ubuntu VM'de (Oracle Cloud Always Free vb.) 7/24 kurar.
# Docker'ı kurar, imajı build eder ve botu otomatik-yeniden-başlatmalı çalıştırır.
#
# Kullanım (repo kök dizininde):
#   TELEGRAM_BOT_TOKEN=123456:GERCEK_TOKEN bash deploy/setup.sh
#
# Ya da: repo kökünde bir .env dosyası oluşturup (TELEGRAM_BOT_TOKEN=... satırıyla)
# sadece `bash deploy/setup.sh` çalıştır — token her seferinde elle verilmez.
set -euo pipefail

# Elle/CI'dan verilen TELEGRAM_BOT_TOKEN her zaman .env'deki degerden onceliklidir.
_token_from_caller="${TELEGRAM_BOT_TOKEN:-}"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
if [[ -n "$_token_from_caller" ]]; then
  TELEGRAM_BOT_TOKEN="$_token_from_caller"
fi

: "${TELEGRAM_BOT_TOKEN:?HATA: TELEGRAM_BOT_TOKEN tanimli degil (ortam degiskeni olarak ver ya da repo kokunde .env dosyasi olustur)}"

# Docker'ın sunucuda önceden manuel olarak kurulmuş olduğu varsayılır.

echo "==> Imaj build ediliyor..."
docker build -t stock-tracker .

echo "==> Eski konteyner varsa kaldiriliyor..."
docker rm -f stock-tracker 2>/dev/null || true

# Konteyner artik root degil, botuser (uid 1000) olarak calisiyor. Volume root
# olarak calisan eski surumde olustuysa /data root'a ait olur ve bot SQLite
# dosyasina yazamaz. Asagidaki chown ilk geciste bunu duzeltir, sonraki
# deploy'larda no-op'tur. Ayri bir yardimci image cekmemek icin zaten build
# edilmis stock-tracker image'i --user 0 ile kullaniliyor.
echo "==> Volume sahipligi (uid 1000) kontrol ediliyor..."
docker run --rm --user 0 -v stock_tracker_data:/data stock-tracker \
  chown -R 1000:1000 /data

echo "==> Bot baslatiliyor (7/24, otomatik yeniden baslatmali)..."
# DB_URL bilerek forward edilmiyor: Dockerfile'daki /data yolu, asagidaki
# kalici volume'e (stock_tracker_data) sabit. .env'deki (lokal gelistirme icin
# goreli bir SQLite yolu olabilir) DB_URL buraya sizarsa, veri her yeniden
# deploy'da (docker rm + docker run) konteynerin gecici dosya sistemine yazilip
# kalici volume yerine sessizce kaybolur.
#
# Kaynak limitleri: bot limitsiz birakilirsa bir kacak durumunda VPS'i bogabilir.
# 256m, olculen bos-calisma kullanimina (~55MB RSS) gore genis bir marj birakiyor.
# --memory-swap = --memory olmasi swap'a tasmayi engeller, aksi halde bellek
# limiti anlamsizlasir. Kullanimi izlemek icin: docker stats stock-tracker
docker run -d --name stock-tracker --restart unless-stopped \
  --log-opt max-size=10m --log-opt max-file=3 \
  --memory=256m --memory-swap=256m --cpus=0.5 \
  --pids-limit=100 \
  --security-opt=no-new-privileges --cap-drop=ALL \
  -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -e POLL_INTERVAL_MINUTES="${POLL_INTERVAL_MINUTES:-10}" \
  -v stock_tracker_data:/data \
  stock-tracker

echo ""
echo "Tamam! Loglari izle:   docker logs -f stock-tracker"
echo "Durum:                 docker ps"
