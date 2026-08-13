# 🛍️ StockTracker Bot

Hepimizin başına gelmiştir: O çok beğendiğin kıyafeti bulursun ama tam senin bedenin tükenmiştir! Sürekli siteye girip çıkmaktan yorulmadın mı? İşte **StockTracker Bot** tam olarak bu sorunu çözmek için doğdu.

Bu bot, Zara ve DeFacto gibi mağazalardaki ürünlerin stok durumunu senin yerine 7/24 takip eder. İstediğin beden tekrar stoğa girdiğinde sana Telegram üzerinden anında mesaj atar. Üstelik bunu yaparken spam yapmaz, seni darlamaz; sadece stok geldiğinde tek bir bildirim gönderir.

## ✨ Neler Yapabiliyor?

- 🔗 **Kolay Kullanım:** Sadece ürün linkini kopyalayıp bota yapıştır. Bot sana tüm bedenleri ve stok durumlarını (✅/❌) butonlar halinde sunar.
- 🔔 **Akıllı Bildirim:** Takip ettiğin beden stoğa girdiğinde anında haberin olur. Stok tekrar bitip gelene kadar aynı ürün için bir daha bildirim almazsın.
- 📋 **Takip Listesi:** `/liste` komutuyla neleri takip ettiğini görebilir, tek tıkla takibi bırakabilirsin.
- ⏱ **Sessiz Çalışan İşçi:** Bot arka planda (varsayılan olarak 10 dakikada bir) tüm ürünleri kontrol eder.
- 💾 **Hafif ve Hızlı:** Standart olarak SQLite kullanır ama istersen PostgreSQL gibi daha büyük veritabanlarına da kolayca bağlanabilir.

## 🏪 Desteklenen Mağazalar

| Mağaza | Durum | Teknik Detay |
|---|---|---|
| **Zara** | ✅ Aktif | Kendi API'si üzerinden JSON çekilerek çok hızlı çalışır. |
| **DeFacto** | ✅ Aktif | Sayfa kaynağından anlık stok miktarı okunur. |
| *Diğerleri* | ❌ Şimdilik Yok | Bershka, H&M, LCW gibi markalar Akamai Bot koruması kullandığı için ücretsiz sunuculardan (veya IP'lerden) erişim zorlukları çıkarabiliyor. |

---

## 🚀 Kendi Botunu Nasıl Kurarsın? (Lokal Kurulum)

Kendi bilgisayarında test etmek oldukça kolaydır. Python 3.13+ yüklü olması yeterlidir.

1. **Bot Token'ı Al:** Telegram'da [@BotFather](https://t.me/BotFather)'a gidip `/newbot` yazarak kendine bir bot oluştur ve verdiği Token'ı kopyala.
2. **Projeyi İndir ve Kur:**
   ```bash
   git clone https://github.com/seniih/stock-tracker-bot.git
   cd stock-tracker-bot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Ayarları Yap:** `.env.example` dosyasının adını `.env` olarak değiştir ve içine kopyaladığın Token'ı yaz:
   ```env
   TELEGRAM_BOT_TOKEN=senin_token_buraya
   ```
4. **Botu Çalıştır!**
   ```bash
   python -m stock_tracker.bot.main
   ```
   Artık Telegram'dan botuna gidip `/start` diyebilirsin!

---

## 🌍 Sunucuya (VPS) Yükleme ve 7/24 Çalıştırma

Botunun bilgisayarını kapattığında bile çalışmaya devam etmesi için onu bir VPS'e (Sanal Sunucu) yüklemelisin. Bu proje, **tam otomatik dağıtım (CI/CD)** için mükemmel şekilde ayarlanmıştır. Docker sayesinde kurulum çok basittir ve kalıcı veritabanı (Volume) kullanır.

### 1. Sunucuyu Hazırla (Sadece 1 Kez)
Sunucuna bağlanıp Docker'ı kur ve projeyi barındıracağın klasörü hazırla:
```bash
sudo apt-get update -y && sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER # Docker'ı şifresiz (sudo'suz) kullanabilmek için

mkdir -p /opt/stock-tracker-bot
cd /opt/stock-tracker-bot
git clone https://github.com/seniih/stock-tracker-bot.git .

# Ayar dosyanı oluştur
nano .env
# İçine şunu yaz ve kaydet: TELEGRAM_BOT_TOKEN=senin_token_buraya
```
*(Grupların güncellenmesi için sunucudan `exit` yazıp çıkın ve tekrar bağlanın).*

### 2. GitHub Actions ile Tam Otomatik Güncelleme
Bilgisayarında kod yazıp GitHub'a yüklediğinde (`git push`), sistemin otomatik olarak sunucuna bağlanıp botu güncellemesi için GitHub Actions (`.github/workflows/deploy.yml`) hazır bekliyor! 

Bunun için GitHub'da projenin **Settings → Secrets and variables → Actions** kısmına şu bilgileri eklemelisin:
- `VPS_HOST`: Sunucunun IP adresi (Örn: 198.51.100.23)
- `VPS_USER`: Sunucudaki kullanıcı adın (Örn: ubuntu, root, senih)
- `VPS_SSH_KEY`: Sunucuya erişim için ürettiğin Özel SSH Anahtarı (Private Key). 
  *(Bu robotun sunucuya girebilmesi için kendi bilgisayarında `ssh-keygen` ile şifresiz bir anahtar üretip, `.pub` uzantılı açık anahtarı sunucundaki `~/.ssh/authorized_keys` dosyasına eklemeyi unutma!)*

**İşte bu kadar!** Artık kodunda bir değişiklik yapıp `main` dalına pushladığında, GitHub robotu sunucuna bağlanacak, yeni kodları indirecek ve botunu otomatik olarak yeniden başlatacaktır. Sen sadece arkanı yaslanıp kahveni yudumlayabilirsin! ☕

---

## 🛠️ Projenin İçi (Geliştiriciler İçin)

Eğer projeyi incelemek veya katkıda bulunmak istersen, yapı oldukça modülerdir:
- `bot/`: Telegram botunun beyni. Handlerlar, klavyeler ve poller burada yönetilir.
- `core/`: Veritabanı işlemleri (SQLAlchemy) ve ayarlar bulunur.
- `adapters/`: Mağazalara özel stok çekme modülleri. Yeni bir mağaza eklemek istersen, `base.py` içindeki taslağı inceleyip kendi mağaza adaptörünü dakikalar içinde yazabilirsin!

Umarım bu bot, kaçırdığın o güzel kıyafetleri yakalamana yardımcı olur! Geliştirmeye, yeni fikirler sunmaya ve yeni mağazalar eklemeye her zaman açığız. Mutlu takipler! 🚀
