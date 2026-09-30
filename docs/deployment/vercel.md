# Vercel + Neon kurulumu

Bu dağıtım Django web sitesi, yönetim paneli, ücretsiz kayıt, QR bilet ve giriş kontrolünü aynı Vercel projesinde çalıştırır. Ayrı backend sunucusu gerekmez. Kalıcı kayıtlar için Neon PostgreSQL gerekir; Vercel'in geçici dosya sistemi veritabanı olarak kullanılmaz.

## 1. Vercel ayarları

- GitHub: `riadosman/tedxgedikuniversity`, branch: `main`.
- Project Name: `tedxgedikuniversity` önerilir; `platform` da çalışır. Gerçek alan adını Vercel belirler.
- Root Directory: `platform`.
- Framework Preset: `Django`.
- Install Command: `pip install -r requirements.txt`.
- Build Command: `python manage.py check --deploy --fail-level WARNING` (vercel.json içinde tanımlı).
- Output Directory: varsayılan / N/A. `staticfiles` yazmayın.
- Python: `.python-version` ile 3.12.

Vercel `manage.py` ve `config.wsgi.application` üzerinden backend'i bulur; `collectstatic` otomatik çalışır. SPA rewrite veya eski `@vercel/python` routes ayarları eklemeyin.

## 2. Neon

Vercel Marketplace > Neon üzerinden veritabanı oluşturup projeye bağlayın. Sunucu ve veritabanı bölgesini mümkün olduğunca aynı seçin. Planın gösterilen limit ve ücretini kontrol edin. İlk aşamada yalnızca Production ortamına bağlayın. Preview için ayrı boş veritabanı veya ayrı Neon branch kullanın; gerçek katılımcı veritabanını preview koduyla paylaşmayın.

Neon'un pooled PostgreSQL bağlantısını `DATABASE_URL` olarak kullanın. Entegrasyon bu değişkeni eklediyse aşağıdaki örnek değerle üzerine yazmayın. Şemayı hazırlamak için Neon'un direct/unpooled bağlantısını yerel kurulum dosyasında kullanabilirsiniz. Her ikisi de aynı veritabanına işaret etmelidir.

## 3. Ortam değişkenleri

`platform/.env.vercel.example` tüm gerekli isimleri içerir. Proje kökünden, gerçek alan adınızla yeni ve bağımsız anahtarlar üretin:

```powershell
.venv/Scripts/python.exe platform/scripts/create_vercel_env.py --domain tedxgedikuniversity.vercel.app --output .local/vercel-production.env
```

Alan adı sadece örnektir; Vercel'de görünen gerçek adresle değiştirin. Üretilen dosyada `DATABASE_URL` satırına Neon bağlantısını yazın. Yerel geliştirme anahtarlarını üretime kopyalamayın. Bu dosya git tarafından dışlanır. İçeriğini Vercel Environment Variables alanına Production için yapıştırın. `EXAMPLE_NAME` gereksizdir.

`CREDENTIAL_KEY` bilet QR verilerini ve bildirimleri şifreler: etkinlik boyunca sabit tutun ve güvenli yedekleyin. Yeniden oluşturmak mevcut şifreli kayıtları okunamaz yapar. `DJANGO_SECRET_KEY` de dağıtımlar arasında korunmalıdır.

İlk kurulumda `OUTGOING_EMAIL_ENABLED=false`: başvuru başarılı olduğunda bilet ve QR doğrudan ekranda görünür. E-posta zorunlu değildir. Katılımcı bileti yazdırmalı veya özel bağlantıyı saklamalıdır. E-posta kurtarma ve ekip davet e-postaları bu modda gönderilmez.

## 4. Veritabanını ve yöneticiyi hazırlama

Bu komutlar bilgisayarınızdan Neon'a bağlanır; bilgisayarınızın sonrasında açık kalması gerekmez. Python ortamı yoksa önce README'deki uv kurulumunu uygulayın. Komutları **repo kökünde**, doldurulmuş env dosyasıyla çalıştırın:

```powershell
$env:TEDX_ENV_FILE = (Resolve-Path .local/vercel-production.env).Path
.venv/Scripts/python.exe platform/manage.py migrate --noinput
.venv/Scripts/python.exe platform/manage.py import_event_sources
.venv/Scripts/python.exe platform/manage.py prepare_public_content
.venv/Scripts/python.exe platform/manage.py prepare_policy_drafts
.venv/Scripts/python.exe platform/manage.py bootstrap_organizer root SENIN_EMAIL_ADRESIN --event tedxgedik
Remove-Item Env:TEDX_ENV_FILE
```

`root` burada seçilen kullanıcı adıdır, sistem/root hesabı değildir. E-posta yer tutucusunu değiştirin. Parola terminalde gizli sorulur; varsayılan parola yoktur. Komut mevcut yöneticinin parolasını değiştirmez. İlk girişte authenticator uygulamasıyla MFA kurun, kurtarma kodlarını saklayın. Django `/admin/` bu projede yoktur; yönetim paneli `/staff/` adresindedir.

Build ve HTTP istekleri migration veya yönetici oluşturmaz. Sonraki şema değişikliklerinde önce yedek alın ve uygun sürümle `migrate` çalıştırın. `prepare_policy_drafts` yalnızca ilk kurulum içindir; yayınlanmış etkinlik üzerinde tekrar çalıştırmayın.

## 5. Biletleri açma

Kaynak veriler taslak olarak içe alınır. `/staff/tedxgedik/settings/` ekranında etkinlik tarihlerini, mekânı, iletişim adresini, kapasiteyi, kayıt başlangıç/bitişini ve bilet tahsis son saatini kontrol edin. Kaynak belgelerdeki eski tarihleri güncel etkinlik bilgisi olarak varsaymayın.

- Katılım türü `free`, kayıt modu `first_come` olmalı.
- Kayıt tarih aralığı şu anı kapsamalı; tahsis son saati gelecekte olmalı.
- Kapasite sıfırdan büyük ve lisanslı kapasite sınırı içinde olmalı.
- KVKK metni, metin sürümü ve kayıt politikası kontrol edilip onaylanmalı.
- Etkinlik `published` olmalı. Gerekli içerik sayfalarını ayrıca yayınlayın.
- `/staff/tedxgedik/ticket-types/` içinde `general` bilet türünü etkinleştirin; kapasiteden düşme açık olmalı.
- Giriş kontrolü için etkinlik günü `entry_mode=online` ve geçerli kapı açılış saati gerekir.

Kayıt önkoşullarını veri oluşturmadan kontrol edin:

```powershell
$env:TEDX_ENV_FILE = (Resolve-Path .local/vercel-production.env).Path
.venv/Scripts/python.exe platform/manage.py check_ticket_launch --event tedxgedik
Remove-Item Env:TEDX_ENV_FILE
```

Canlı alan adında ayrıca kayıt → bilet/QR → yazdırma ve yetkili giriş taraması doğrulanmalıdır. Yerel testlerin geçmesi canlı kurulumun doğrulandığı anlamına gelmez.

## 6. Ayrı bağlantılar

Aşağıda `https://ALAN_ADIN` yerine Vercel'in verdiği gerçek adresi yazın:

| İşlem | Yol |
|---|---|
| Ana sayfa | `/` |
| Yönetici girişi | `/accounts/login/` |
| MFA kurulumu/doğrulaması | `/accounts/mfa/` |
| Yönetim paneli | `/staff/` |
| Etkinlik ayarları | `/staff/tedxgedik/settings/` |
| Katılımcı kaydı | `/e/tedxgedik/register/` |
| Bilet türleri | `/staff/tedxgedik/ticket-types/` |
| Bilet yönetimi | `/staff/tedxgedik/tickets/` |
| QR tarayıcı | `/staff/tedxgedik/check-in/` |
| Bilet kurtarma | `/e/tedxgedik/recover/` (e-posta kapalıysa destek gerekir) |

Kişisel bilet bağlantısı kayıt sonrası üretilen gizli token içerir; ortak/sabit bir bilet bağlantısı yoktur.

## 7. Bu dağıtımın sınırları

- Dosya/fotoğraf yükleme Vercel'de kapalıdır; geçici diske başarılı görünerek veri kaybettirmez. Bu modülü açmak için kalıcı obje depolama ve tarama entegrasyonu gerekir. Logolar/fontlar/CSS gibi repodaki statik dosyalar çalışır.
- E-posta daha sonra açılacaksa gerçek SMTP ayarları, etkinlikte `ticket_email_enabled` ve sürekli bildirim işleyicisi gerekir (`deliver_notifications` komutu). Yalnızca SMTP değişkenlerini eklemek kuyruktaki mesajları göndermez. Mevcut yerel arka plan süreçleri Vercel'e taşınmaz.
- Ücretli ödeme sağlayıcısı entegre değildir; bu kurulum ücretsiz bilet içindir.
- Veritabanı yedekleri ve geri yükleme, Neon planınızın sunduğu özelliklerle ayrıca kurulmalı/doğrulanmalıdır.

Resmî kaynaklar: https://vercel.com/docs/frameworks/full-stack/django ve https://vercel.com/marketplace/neon/neon
