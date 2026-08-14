FROM python:3.13-slim

WORKDIR /app

# Bağımlılıkları önce kur (katman önbelleği için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu
COPY stock_tracker ./stock_tracker

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# SQLite verisi kalıcı disk üzerinde tutulur (varsayılan; env ile değiştirilebilir)
ENV DB_URL=sqlite:////data/stock_tracker.db \
    POLL_INTERVAL_MINUTES=10

# Bot root olarak calismasin. UID 1000 bilerek sabitlendi: deploy/setup.sh
# mevcut volume'un sahipligini ayni UID'ye ceviriyor.
# Yeni olusturulan bir volume, image'daki /data dizininin sahipligini miras alir.
# /app bilerek chown'lanmiyor: uygulama kodu, uygulamanin kendisi tarafindan
# yazilabilir olmamali.
RUN useradd --create-home --shell /usr/sbin/nologin --uid 1000 botuser \
    && mkdir -p /data \
    && chown botuser:botuser /data

USER botuser

CMD ["python", "-m", "stock_tracker.bot.main"]
