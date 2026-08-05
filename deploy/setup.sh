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

echo "==> Docker kuruluyor (gerekliyse)..."
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y docker.io
fi
sudo systemctl enable --now docker

echo "==> Imaj build ediliyor..."
sudo docker build -t stock-tracker .

echo "==> Eski konteyner varsa kaldiriliyor..."
sudo docker rm -f stock-tracker 2>/dev/null || true

echo "==> Bot baslatiliyor (7/24, otomatik yeniden baslatmali)..."
# DB_URL bilerek forward edilmiyor: Dockerfile'daki /data yolu, asagidaki
# kalici volume'e (stock_tracker_data) sabit. .env'deki (lokal gelistirme icin
# goreli bir SQLite yolu olabilir) DB_URL buraya sizarsa, veri her yeniden
# deploy'da (docker rm + docker run) konteynerin gecici dosya sistemine yazilip
# kalici volume yerine sessizce kaybolur.
sudo docker run -d --name stock-tracker --restart unless-stopped \
  --log-opt max-size=10m --log-opt max-file=3 \
  -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -e POLL_INTERVAL_MINUTES="${POLL_INTERVAL_MINUTES:-10}" \
  -v stock_tracker_data:/data \
  stock-tracker

echo ""
echo "Tamam! Loglari izle:   sudo docker logs -f stock-tracker"
echo "Durum:                 sudo docker ps"
