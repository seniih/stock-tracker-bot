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

CMD ["python", "-m", "stock_tracker.bot.main"]
