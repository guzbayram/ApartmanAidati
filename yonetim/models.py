from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
import random
import string
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os
from django.utils.translation import gettext_lazy as _
from django.apps import apps

# Turkish character mapping for username generation
# Türkçe karakter eşleme tablosu kullanıcı adı üretimi için
TURKISH_CHAR_MAP = {
    'ç': 'c', 'Ç': 'C',
    'ğ': 'g', 'Ğ': 'G',
    'ı': 'i', 'İ': 'I',
    'ö': 'o', 'Ö': 'O',
    'ş': 's', 'Ş': 'S',
    'ü': 'u', 'Ü': 'U',
}

def generate_unique_username(first_name, last_name, site_code):
    """
    Generates a unique username.
    Benzersiz bir kullanıcı adı üretir.
    Format: ad.soyad_sitekodu_rastgele
    """
    # Transliterate Turkish characters / Türkçe karakterleri çevir
    first_name_slug = "".join(TURKISH_CHAR_MAP.get(c, c) for c in first_name.lower())
    last_name_slug = "".join(TURKISH_CHAR_MAP.get(c, c) for c in last_name.lower())
    
    base_username = f"{slugify(first_name_slug)}.{slugify(last_name_slug)}_{slugify(site_code)}"
    
    # Generate random suffix / Rastgele bir sonek üret
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    username = f"{base_username}_{random_suffix}"
    
    # Ensure uniqueness / Benzersizliği sağla
    Kullanici = apps.get_model('yonetim', 'Kullanici')
    while Kullanici.objects.filter(username=username).exists():
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        username = f"{base_username}_{random_suffix}"
        
    return username

class Kullanici(AbstractUser):
    """
    Custom User Model.
    Özel Kullanıcı Modeli.
    """
    # AbstractUser'dan gelen username alanını override ediyoruz
    # Override the username field from AbstractUser
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,  # Django'nun USERNAME_FIELD gerekliliği için unique olmalı
        help_text=_("Required. 150 characters or fewer."),
        validators=[AbstractUser.username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )

    # AbstractUser'dan gelen email alanını override ediyoruz.
    # We are overriding the email field from AbstractUser.
    email = models.EmailField(_("email address"), blank=True, null=True)

    site_kodu = models.CharField(max_length=100, blank=True, null=True, verbose_name="Site Kodu")
    is_yonetici = models.BooleanField(default=False, verbose_name="Yönetici mi?")
    # Daire'ye ForeignKey, Daire modeli aşağıda tanımlanacak.
    # ForeignKey to Daire, Daire model will be defined below.
    aktif_daire = models.ForeignKey('Daire', on_delete=models.SET_NULL, null=True, blank=True, related_name='aktif_kullanicisi', verbose_name="Aktif Daire")

    # Kullanıcı adı ve site kodu birlikte benzersiz olmalı
    # Username and site code must be unique together
    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"
        ordering = ['first_name', 'last_name']
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'site_kodu'],
                name='unique_username_per_site',
                violation_error_message="Bu kullanıcı adı bu site için zaten kullanılıyor."
            )
        ]

    def save(self, *args, **kwargs):
        """
        Kullanıcı adını site kodu ile birleştirerek benzersiz yap
        Make username unique by combining it with site code
        """
        if self.site_kodu:
            # Eğer kullanıcı adı zaten site kodu içermiyorsa, ekle
            # If username doesn't already contain site code, add it
            if not self.username.endswith(f"_{self.site_kodu}"):
                self.username = f"{self.username}_{self.site_kodu}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username

class Site(models.Model):
    """
    Site/Apartment complex model.
    Site/Apartman kompleksi modeli.
    """
    ad = models.CharField(max_length=200, verbose_name="Site Adı")
    adres = models.CharField(max_length=500, verbose_name="Adres")
    kod = models.CharField(max_length=50, unique=True, verbose_name="Site Kodu")
    # Yönetici, Kullanici modeline ForeignKey.
    # Manager, ForeignKey to Kullanici model.
    yonetici = models.ForeignKey(Kullanici, on_delete=models.PROTECT, related_name='yonettigi_siteler', verbose_name="Yönetici")

    # Yönetici İletişim Bilgileri / Manager Contact Information
    yonetici_adi = models.CharField(max_length=150, blank=True, verbose_name="Yönetici Adı Soyadı")
    yonetici_email = models.EmailField(blank=True, verbose_name="Yönetici E-postası")

    # Finansal Ayarlar / Financial Settings
    aidat_miktari = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Varsayılan Aidat Miktarı")
    gecikme_faizi_orani = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, help_text="Örn: 0.0050 (yani %0.5). Günlük uygulanacak faiz oranı.", verbose_name="Gecikme Faizi Oranı (Günlük)")
    son_odeme_gunu_oncesi_hatirlatma = models.PositiveIntegerField(default=0, help_text="Aidat son ödeme gününden kaç gün önce hatırlatma maili gönderilsin? (0 pasif yapar)", verbose_name="Hatırlatma Günü Sayısı")

    # Genel Ayarlar / General Settings
    otomatik_mail_aktif = models.BooleanField(default=False, verbose_name="Otomatik Mail Gönderimi Aktif mi?")
    makbuz_yukleme_aktif = models.BooleanField(default=True, verbose_name="Aidat/Gider Makbuzu Yükleme Aktif mi?")
    logo = models.ImageField(upload_to='site_logolari/', null=True, blank=True, verbose_name="Site Logosu")
    duyurular = models.TextField(blank=True, verbose_name="Duyurular")
    site_kurallari = models.TextField(blank=True, verbose_name="Site Kuralları")

    # Eski Alanlar (Bu daha önce eklenmişti, yerini koruyoruz)
    # Old Fields (This was added before, keeping its place)
    tanimli_gider_turleri = models.TextField(null=True, blank=True, help_text="Virgülle ayırarak gider türlerini giriniz (örn: Elektrik,Su,Asansör Bakımı).", verbose_name="Tanımlı Gider Türleri")

    def __str__(self):
        return self.ad

    class Meta:
        verbose_name = "Site"
        verbose_name_plural = "Siteler"
        ordering = ['ad']

class Blok(models.Model):
    """
    Building Block model within a Site.
    Site içindeki Bina Blok modeli.
    """
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='bloklar', verbose_name="Site")
    ad = models.CharField(max_length=50, verbose_name="Blok Adı")
    aidat_miktari = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Blok Aidat Miktarı",
        help_text="Bu blok için özel aidat miktarı. Boş bırakılırsa site genel aidat miktarı kullanılır."
    )
    aciklama = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Blok Açıklaması",
        help_text="Blok hakkında ek bilgiler"
    )

    def save(self, *args, **kwargs):
        # Automatically convert 'ad' to uppercase before saving.
        # Kaydetmeden önce 'ad' alanını otomatik olarak büyük harfe çevir.
        self.ad = self.ad.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.site.ad} - {self.ad.upper()}"

    @property
    def daire_sayisi(self):
        """
        Bloktaki daire sayısını döndürür
        Returns the number of flats in the block
        """
        return self.daireler.count()

    @property
    def dolu_daire_sayisi(self):
        """
        Bloktaki dolu daire sayısını döndürür
        Returns the number of occupied flats in the block
        """
        return self.daireler.filter(is_dolu=True).count()

    class Meta:
        verbose_name = "Blok"
        verbose_name_plural = "Bloklar"
        ordering = ['ad']
        unique_together = ('site', 'ad') # Ensure block names are unique within a site / Blok adlarının site içinde benzersiz olmasını sağla


class Daire(models.Model):
    """
    Apartment/Flat model within a Blok.
    Blok içindeki Daire modeli.
    """
    blok = models.ForeignKey(Blok, on_delete=models.CASCADE, related_name='daireler', verbose_name="Blok")
    daire_no = models.CharField(max_length=20, verbose_name="Daire No")
    # Kullanici'ya OneToOneField, null olabilir çünkü daire boş olabilir.
    # OneToOneField to Kullanici, can be null as flat might be empty.
    kullanici = models.OneToOneField(Kullanici, on_delete=models.SET_NULL, null=True, blank=True, related_name='sakin_oldugu_daire', verbose_name="Sakin")
    telefon_no = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefon Numarası")
    
    # DaireForm'dan gelen yeni alanlar - New fields from DaireForm
    DAIRE_TIPLERI = [
        ('1+1', '1+1'),
        ('2+1', '2+1'),
        ('3+1', '3+1'),
        ('4+1', '4+1'),
        ('5+1', '5+1'),
        ('dublex', 'Dublex'),
        ('isyeri', 'İş Yeri'),
        ('diger', 'Diğer'),
    ]
    daire_tipi = models.CharField(max_length=20, choices=DAIRE_TIPLERI, default='diger', null=True, blank=True, verbose_name="Daire Tipi")
    m2_brut = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Brüt Metrekare")
    m2_net = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Net Metrekare")
    is_dolu = models.BooleanField(default=True, verbose_name="Daire Dolu mu?")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Daire Açıklaması")
    # Mevcut alanlar devam ediyor - Existing fields continue
    devir_bakiye_gecen_yil = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Devir Bakiye (Geçen Yıldan)")
    devir_bakiye_yili = models.IntegerField(null=True, blank=True, verbose_name="Devir Bakiye Yılı")

    def __str__(self):
        return f"{self.blok.ad} - Daire {self.daire_no}"

    @property
    def daire_tam_adi(self):
        """
        Returns the full name of the flat (e.g., A BLOK - Daire 1).
        Dairenin tam adını döndürür (örn: A BLOK - Daire 1).
        """
        return f"{self.blok.ad} - Daire {self.daire_no}"

    def get_sortable_daire_no(self):
        """
        Helper for natural sorting of daire_no. Separates numeric and non-numeric parts.
        Daire no'sunun doğal sıralaması için yardımcı. Sayısal ve sayısal olmayan kısımları ayırır.
        Example: '1A' -> (1, 'A'), '10' -> (10, '')
        """
        num_part = ""
        str_part = ""
        for char in self.daire_no:
            if char.isdigit():
                num_part += char
            else:
                str_part += char
        return (int(num_part) if num_part else 0, str_part.lower())


    class Meta:
        verbose_name = "Daire"
        verbose_name_plural = "Daireler"
        ordering = ['blok', 'daire_no'] # Consider using a custom ordering based on get_sortable_daire_no if needed for complex cases
        unique_together = ('blok', 'daire_no') # Ensure flat numbers are unique within a block / Daire numaralarının blok içinde benzersiz olmasını sağla


class Aidat(models.Model):
    """
    Dues/Fee model for a Daire.
    Bir Daire için Aidat modeli.
    """
    # ODEME_YONTEMLERI artık kullanılmayacak, bu yüzden kaldırıyoruz.
    # ODEME_YONTEMLERI will no longer be used, so we are removing it.
    # ODEME_YONTEMLERI = [
    #     ('nakit', 'Nakit'),
    #     ('kredi_karti', 'Kredi Kartı'),
    #     ('banka_havalesi', 'Banka Havalesi/EFT'),
    #     ('diger', 'Diğer'),
    # ]

    daire = models.ForeignKey(Daire, on_delete=models.CASCADE, related_name='aidatlar', verbose_name="Daire")
    tutar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tutar")
    tarih = models.DateField(null=True, blank=False, verbose_name="Ödeme Tarihi/Vadesi") # Made blank=False as date is usually crucial
    aciklama = models.CharField(max_length=255, blank=True, verbose_name="Açıklama")
    # odeme_yontemi alanı kaldırılıyor.
    # The odeme_yontemi field is being removed.
    # odeme_yontemi = models.CharField(
    #     max_length=20,
    #     choices=ODEME_YONTEMLERI,
    #     default='diger',
    #     verbose_name="Ödeme Yöntemi",
    #     null=True, blank=True # Formda zorunlu olmaması için, veya default bir değer atanabilir
    # )
    makbuz = models.FileField(upload_to='aidat_makbuzlari/', null=True, blank=True, verbose_name="Makbuz")

    def __str__(self):
        return f"{self.daire} - {self.tutar} TL ({self.tarih.strftime('%d-%m-%Y') if self.tarih else 'Tarih Yok'})"

    class Meta:
        verbose_name = "Aidat Kaydı"
        verbose_name_plural = "Aidat Kayıtları"
        ordering = ['-tarih', '-id']


class Gider(models.Model):
    """
    Expense model for a Site.
    Bir Site için Gider modeli.
    """
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='giderler', verbose_name="Site")
    tur = models.CharField(max_length=100, verbose_name="Gider Türü")
    tutar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tutar")
    tarih = models.DateField(null=True, blank=False, verbose_name="Gider Tarihi") # Made blank=False
    aciklama = models.CharField(max_length=255, blank=True, verbose_name="Açıklama")
    makbuz = models.FileField(upload_to='gider_makbuzlari/', null=True, blank=True, verbose_name="Makbuz/Fatura")

    def __str__(self):
        return f"{self.tur} - {self.tutar} TL ({self.tarih.strftime('%d-%m-%Y') if self.tarih else 'Tarih Yok'})"

    class Meta:
        verbose_name = "Gider Kaydı"
        verbose_name_plural = "Gider Kayıtları"
        ordering = ['-tarih', '-id']


class YillikRaporPDF(models.Model):
    """
    Model to store generated annual PDF reports.
    Oluşturulan yıllık PDF raporlarını saklamak için model.
    """
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='yillik_raporlar', verbose_name="Site")
    yil = models.IntegerField(verbose_name="Rapor Yılı")
    pdf_dosyasi = models.FileField(upload_to='yillik_raporlar/', verbose_name="PDF Dosyası")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    rapor_basligi = models.CharField(max_length=255, blank=True, verbose_name="Rapor Başlığı")

    def save(self, *args, **kwargs):
        # Automatically populate rapor_basligi if it's empty.
        # Eğer boşsa rapor_basligi alanını otomatik olarak doldur.
        if not self.rapor_basligi:
            self.rapor_basligi = f"{self.site.ad} - {self.yil} YILI SONU RAPORU"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete the associated PDF file from disk when the model instance is deleted.
        # Model örneği silindiğinde ilişkili PDF dosyasını diskten sil.
        if self.pdf_dosyasi:
            if os.path.isfile(self.pdf_dosyasi.path):
                os.remove(self.pdf_dosyasi.path)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return self.rapor_basligi or f"{self.site.ad} - {self.yil} Raporu"

    class Meta:
        verbose_name = "Yıllık Rapor PDF"
        verbose_name_plural = "Yıllık Rapor PDF'leri"
        ordering = ['site', '-yil', '-olusturulma_tarihi']
        unique_together = ('site', 'yil') # Ensure one report per site per year / Her site için yılda bir rapor olmasını sağla

# Signal to delete PDF file when YillikRaporPDF instance is deleted using QuerySet.delete()
# YillikRaporPDF örneği QuerySet.delete() ile silindiğinde PDF dosyasını silmek için sinyal
@receiver(post_delete, sender=YillikRaporPDF)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `YillikRaporPDF` object is deleted.
    İlgili `YillikRaporPDF` nesnesi silindiğinde
    dosyayı dosya sisteminden siler.
    """
    if instance.pdf_dosyasi:
        if os.path.isfile(instance.pdf_dosyasi.path):
            os.remove(instance.pdf_dosyasi.path)
