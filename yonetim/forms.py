from django import forms
from .models import Aidat, Gider, Site, Daire, Kullanici, Blok
from django.forms.widgets import DateInput
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from .models import generate_unique_username
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

class AidatForm(forms.ModelForm):
    """
    Form for creating and updating Aidat records.
    Aidat kayıtları oluşturmak ve güncellemek için form.
    """
    def __init__(self, *args, **kwargs):
        site = kwargs.pop('site', None)
        daire_id = kwargs.pop('daire_id', None) # panel_view'dan gelen daire_id
        panel_form = kwargs.pop('panel_form', False) # panelde mi kullanılıyor?
        super().__init__(*args, **kwargs)

        # Tarih alanı için DateInput widget'ı ekle
        # Add DateInput widget for the date field
        self.fields['tarih'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['tutar'].widget.attrs.update({'class': 'form-control', 'min': '0.01'})
        self.fields['aciklama'].widget.attrs.update({'class': 'form-control', 'rows': 3})
        self.fields['makbuz'].widget.attrs.update({'class': 'form-control'})
        
        if panel_form and daire_id:
            # Eğer panelde kullanılıyorsa ve daire_id belliyse, daire alanına gerek yok (view'da atanacak).
            # If used in the panel and daire_id is known, the daire field is not needed (will be assigned in the view).
            if 'daire' in self.fields:
                del self.fields['daire'] # Daire alanını formdan kaldır
                # self.fields['daire'].required = False
                # Formda görünmemesi için widget'ı da gizleyebiliriz, ancak validasyon için kalması daha iyi olabilir.
                # We can also hide the widget so it doesn't appear in the form, but it might be better to keep it for validation.
                # self.fields['daire'].widget = forms.HiddenInput()
        elif site: # Yönetici aidat ekleme/düzenleme ekranında (panel dışı)
            # Daireleri siteye göre filtrele
            # Filter flats by site
            self.fields['daire'].queryset = Daire.objects.filter(blok__site=site).order_by('blok__ad', 'daire_no')
            self.fields['daire'].widget.attrs.update({'class': 'form-select'})
        elif not self.instance.pk: # Yeni kayıt ve site bilgisi yoksa (genel durum, olmamalı ama)
             self.fields['daire'].queryset = Daire.objects.none()

        # Checkbox'lar için özel class ataması
        # Custom class assignment for checkboxes
        # Bootstrap 5'te checkboxlar genellikle input group veya form-check ile sarılır, 
        # doğrudan input'a class vermek her zaman istenen sonucu vermeyebilir.
        # Gerekirse template'te widget render ederken bu class'ları kullanabiliriz.
        # if 'is_odendi' in self.fields:
        # self.fields['is_odendi'].widget.attrs.update({'class': 'form-check-input'}) # Bootstrap 5 için

    class Meta:
        model = Aidat
        fields = ['daire', 'tutar', 'tarih', 'aciklama', 'makbuz'] # 'odeme_yontemi' kaldırıldı
        # 'daire' alanı __init__ içinde yönetildiği için burada kalabilir veya duruma göre çıkarılabilir.
        # Since the 'daire' field is managed in __init__, it can remain here or be removed depending on the situation.
        # Eğer panel_form=True ise zaten siliniyor.
        # If panel_form=True, it is already being deleted.


class GiderForm(forms.ModelForm):
    """
    Form for creating and updating Gider records.
    Gider kayıtları oluşturmak ve güncellemek için form.
    """
    def __init__(self, *args, **kwargs):
        site = kwargs.pop('site', None) # site bilgisini al
        panel_form = kwargs.pop('panel_form', False)
        super().__init__(*args, **kwargs)

        self.fields['tarih'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['tutar'].widget.attrs.update({'class': 'form-control', 'min': '0.01'})
        self.fields['aciklama'].widget.attrs.update({'class': 'form-control', 'rows': 3})
        self.fields['tur'].widget.attrs.update({'class': 'form-select'})
        self.fields['makbuz'].widget.attrs.update({'class': 'form-control'})

        if panel_form and site:
            # Panelde kullanılıyorsa site zaten view'dan geliyor, formda göstermeye gerek yok.
            # If used in the panel, site already comes from the view, no need to show it in the form.
            if 'site' in self.fields:
                 del self.fields['site']
        elif not self.instance.pk and not site: # Yeni kayıt, site yok (genel durum)
            # Bu durumda site alanı boş olmamalı, normalde view site bilgisini sağlar.
            # In this case, the site field should not be empty, normally the view provides site information.
            # Belki bir hata mesajı veya varsayılan bir davranış eklenebilir.
            # Maybe an error message or a default behavior can be added.
            pass
        # Eğer site alanı formda kalacaksa (örneğin süper admin farklı sitelere gider girebiliyorsa)
        # ve site queryset'i ayarlanmadıysa, burası uygun olabilir.
        # if 'site' in self.fields and not self.fields['site'].queryset:
        # self.fields['site'].queryset = Site.objects.all() # Ya da kullanıcının yetkili olduğu siteler
        # self.fields['site'].widget.attrs.update({'class': 'form-select'})


    class Meta:
        model = Gider
        fields = ['site', 'tutar', 'tarih', 'aciklama', 'tur', 'makbuz']
        # 'site' alanı __init__ içinde yönetildiği için burada kalabilir veya panel_form=True ise silinebilir.
        # The 'site' field is managed in __init__, so it can remain here or be deleted if panel_form=True.


class KullaniciGirisForm(AuthenticationForm):
    """
    Custom login form to apply Bootstrap classes.
    Bootstrap sınıflarını uygulamak için özel giriş formu.
    """
    username = forms.CharField(
        label="Kullanıcı Adı",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm', 
            'placeholder': 'Kayıt olurken belirlediğiniz kullanıcı adınızı giriniz'
        })
    )
    site_kodu = forms.CharField(
        label="Site Kodu",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Site Kodunuz'})
    )
    password = forms.CharField(
        label="Şifre (İsteğe Bağlı)",
        required=False,  # Şifre alanını opsiyonel yap
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Şifreniz (İsteğe Bağlı)'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.required:  # Sadece zorunlu alanları işaretle
                field.label_suffix = " *"
            current_class = field.widget.attrs.get('class', '')
            if 'form-control' not in current_class:
                field.widget.attrs['class'] = f'{current_class} form-control form-control-sm'.strip()

    def clean(self):
        """
        Özel temizleme metodu - Custom cleaning method
        Şifre alanı boş olsa bile kullanıcı adı ve site koduna göre giriş yapılmasına izin ver
        Allow login by username and site code even if password field is empty
        """
        print("\n---------- GİRİŞ FORM CLEAN BAŞLADI ----------")
        username = self.cleaned_data.get('username')
        site_kodu = self.cleaned_data.get('site_kodu')
        password = self.cleaned_data.get('password')

        print(f"Giriş denemesi:")
        print(f"- Kullanıcı adı: {username}")
        print(f"- Site kodu: {site_kodu}")
        print(f"- Şifre girildi mi: {'Evet' if password else 'Hayır'}")

        if not username:
            print("HATA: Kullanıcı adı boş!")
            raise forms.ValidationError(_("Kullanıcı adı gereklidir."))
        
        if not site_kodu:
            print("HATA: Site kodu boş!")
            raise forms.ValidationError(_("Site kodu gereklidir."))

        # Kullanıcı adı ve site kodunu birleştir
        # Combine username and site code
        full_username = f"{username}_{site_kodu}"
        print(f"Oluşturulan tam kullanıcı adı: {full_username}")
        
        try:
            # Önce site kodunun varlığını kontrol et
            # First check if site code exists
            from .models import Site
            if not Site.objects.filter(kod=site_kodu).exists():
                print(f"HATA: Site kodu bulunamadı: {site_kodu}")
                raise forms.ValidationError(_("Bu site kodu sistemde kayıtlı değil."))

            # Sonra kullanıcıyı kontrol et
            # Then check the user
            user = Kullanici.objects.get(username=full_username)
            print(f"Kullanıcı bulundu:")
            print(f"- ID: {user.id}")
            print(f"- Tam kullanıcı adı: {user.username}")
            print(f"- Site kodu: {user.site_kodu}")
            print(f"- Şifre durumu: {'Şifre var' if user.has_usable_password() else 'Şifre yok'}")
            
            if not password:  # Şifre boşsa direkt giriş yap
                print("Şifre boş, direkt giriş yapılıyor")
                return {'username': full_username, 'site_kodu': site_kodu, 'password': None}
            else:
                print("Şifre girilmiş, normal authentication yapılacak")
                # Kullanıcı adını tam haliyle güncelle
                # Update username with full version
                self.cleaned_data['username'] = full_username

        except Kullanici.DoesNotExist:
            print(f"HATA: Kullanıcı bulunamadı: {full_username}")
            # Mevcut kullanıcıları kontrol et ve önerilerde bulun
            # Check existing users and make suggestions
            from django.db.models import Q
            similar_users = Kullanici.objects.filter(
                Q(username__startswith=f"{username}_") | 
                Q(site_kodu=site_kodu)
            ).values_list('username', 'site_kodu')
            
            if similar_users:
                print("Benzer kullanıcılar bulundu:")
                for u, s in similar_users:
                    print(f"- {u} (Site: {s})")
                error_msg = _("Bu kullanıcı adı ve site kodu kombinasyonu bulunamadı. ")
                if any(s == site_kodu for _, s in similar_users):
                    error_msg += _("Bu site kodunda farklı kullanıcı adları var.")
                elif any(u.startswith(f"{username}_") for u, _ in similar_users):
                    error_msg += _("Bu kullanıcı adı farklı site kodlarında kullanılıyor.")
                raise forms.ValidationError(error_msg)
            else:
                raise forms.ValidationError(_("Bu kullanıcı adı ve site kodu kombinasyonu bulunamadı."))

        print("---------- GİRİŞ FORM CLEAN TAMAMLANDI ----------\n")
        return super().clean()  # Normal doğrulama için üst sınıfın clean metodunu çağır


class KullaniciKayitForm(forms.ModelForm):
    """
    Form for new user registration, including Site, Blok, and Daire creation.
    Artık forms.ModelForm'dan miras alıyor. Şifreler test için pasif.
    """
    # Kullanıcı Bilgileri (Modelde olanlar)
    username = forms.CharField(
        label="Kullanıcı Adı",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    first_name = forms.CharField(
        label="Adınız",
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    last_name = forms.CharField(
        label="Soyadınız",
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    email = forms.EmailField(
        label="E-posta Adresiniz (İsteğe Bağlı)",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-sm'})
    )

    # Site, Blok, Daire bilgileri (Bunlar modelde değil, formda kalacak)
    site_ad = forms.CharField(
        label="Site Adı",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    site_adres = forms.CharField(
        label="Site Adresi",
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2})
    )
    site_kod = forms.CharField(
        label="Site Kodu (Benzersiz Olmalı)",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    blok_ad = forms.CharField(
        label="Blok Adı (Örn: A Blok)",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    daire_no = forms.CharField(
        label="Daire Numaranız",
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    telefon_no = forms.CharField(
        label="Telefon Numaranız (İsteğe Bağlı)",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )

    class Meta:
        model = Kullanici 
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        form_fields_for_styling = [
            'username', 'first_name', 'last_name', 'email',
            'site_ad', 'site_adres', 'site_kod', 
            'blok_ad', 'daire_no', 'telefon_no'
        ]        
        for field_name in form_fields_for_styling:
            if field_name in self.fields:
                field = self.fields[field_name]
                current_class = field.widget.attrs.get('class', '')
                if 'form-control-sm' not in current_class:
                    field.widget.attrs['class'] = f'{current_class} form-control form-control-sm'.strip()
                if field.required:
                    field.label_suffix = " *"

    def clean(self):
        cleaned_data = super().clean()
        site_kod = cleaned_data.get('site_kod')
        blok_ad = cleaned_data.get('blok_ad')
        daire_no = cleaned_data.get('daire_no')
        username = cleaned_data.get('username')

        print(f"---------- FORM CLEAN METODU ----------")
        print(f"Site kodu: {site_kod}")
        print(f"Blok adı: {blok_ad}")
        print(f"Daire no: {daire_no}")
        print(f"Kullanıcı adı: {username}")

        # Site kodu kontrolü
        if not site_kod:
            print("Site kodu boş!")
            self.add_error('site_kod', "Site kodu gereklidir.")
            return cleaned_data

        # Kullanıcı adı kontrolü
        if username and site_kod:
            # Kullanıcı adına site kodunu ekle
            # Add site code to username
            full_username = f"{username}_{site_kod}"
            print(f"Tam kullanıcı adı: {full_username}")
            
            if Kullanici.objects.filter(username=full_username).exists():
                print(f"Bu kullanıcı adı ({username}) bu site ({site_kod}) için zaten kullanılıyor!")
                self.add_error('username', 
                    f"Bu kullanıcı adı ({username}) bu site ({site_kod}) için zaten kullanılıyor. "
                    "Farklı bir kullanıcı adı seçiniz veya farklı bir site kodu giriniz."
                )
            else:
                print(f"Bu kullanıcı adı ({username}) bu site ({site_kod}) için kullanılabilir.")
                # Kullanıcı adını güncelle
                # Update username
                cleaned_data['username'] = full_username

        # Blok ve daire no kontrolü
        if site_kod and blok_ad and daire_no:
            try:
                site = Site.objects.get(kod=site_kod)
                print(f"Site bulundu: {site.ad}")
                
                if Blok.objects.filter(site=site, ad=blok_ad.upper(), daireler__daire_no=daire_no).exists():
                    print(f"Bu blok ({blok_ad}) ve daire ({daire_no}) bu site ({site_kod}) için zaten mevcut!")
                    self.add_error('daire_no', 
                        f"'{blok_ad.upper()}' bloğunda '{daire_no}' numaralı daire bu site için zaten mevcut. "
                        "Farklı bir site kodu kullanabilirsiniz."
                    )
                else:
                    print(f"Bu blok ({blok_ad}) ve daire ({daire_no}) bu site ({site_kod}) için kullanılabilir.")
            except Site.DoesNotExist:
                print(f"Site bulunamadı ({site_kod}), yeni site oluşturulacak.")
                pass 

        print("---------- FORM CLEAN METODU TAMAMLANDI ----------")
        return cleaned_data

    def clean_username(self):
        """
        Sadece temel validasyon yap, detaylı kontroller clean metodunda yapılıyor
        Only do basic validation, detailed checks are in clean method
        """
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Kullanıcı adı gereklidir.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Kullanici.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Bu e-posta adresi zaten kullanılıyor."))
        return email

    @transaction.atomic
    def save(self, commit=True):
        print("---------- KAYIT FORM SAVE BAŞLADI ----------")
        user = super().save(commit=False) 
        
        cleaned_data = self.cleaned_data
        print(f"Temizlenmiş veriler: {cleaned_data}")
        
        # Kullanıcı adı artık formdan geliyor, otomatik oluşturmaya gerek yok
        # Username now comes from form, no need for auto-generation
        user.username = cleaned_data.get('username')
        print(f"Kullanıcı adı: {user.username}")
        
        user.first_name = cleaned_data.get('first_name')
        user.last_name = cleaned_data.get('last_name')
        user.email = cleaned_data.get('email') if cleaned_data.get('email') else None
        
        user.site_kodu = cleaned_data.get('site_kod')
        print(f"Site kodu atandı: {user.site_kodu}")
        
        # Şifre atamasını kaldırdık - Removed password assignment
        user.set_unusable_password()  # Şifre kullanılmayacak olarak işaretle
        print("Şifre kullanılmayacak olarak işaretlendi")

        if commit:
            print("Kullanıcı kaydediliyor...")
            user.save()
            print(f"Kullanıcı kaydedildi. ID: {user.id}")
            
            site_ad_form = cleaned_data.get('site_ad')
            site_adres_form = cleaned_data.get('site_adres')
            site_kod_form = cleaned_data.get('site_kod')
            blok_ad_form = cleaned_data.get('blok_ad')
            daire_no_form = cleaned_data.get('daire_no')
            telefon_no_form = cleaned_data.get('telefon_no')

            print(f"Site oluşturuluyor: {site_kod_form}")
            site_instance, site_created = Site.objects.get_or_create(
                kod=site_kod_form,
                defaults={
                    'ad': site_ad_form,
                    'adres': site_adres_form,
                    'yonetici': user
                }
            )
            print(f"Site {'oluşturuldu' if site_created else 'mevcut'}. ID: {site_instance.id}")

            if site_created:
                user.is_yonetici = True
                user.save(update_fields=['is_yonetici'])
                print("Kullanıcı site yöneticisi olarak atandı")
            elif not site_instance.yonetici:
                site_instance.yonetici = user
                site_instance.save(update_fields=['yonetici'])
                user.is_yonetici = True 
                user.save(update_fields=['is_yonetici'])
                print("Kullanıcı mevcut sitenin yöneticisi olarak atandı")

            print(f"Blok oluşturuluyor: {blok_ad_form}")
            blok_instance, blok_created = Blok.objects.get_or_create(
                site=site_instance,
                ad=blok_ad_form.upper(),
                defaults={'site': site_instance, 'ad': blok_ad_form.upper()}
            )
            print(f"Blok {'oluşturuldu' if blok_created else 'mevcut'}. ID: {blok_instance.id}")

            print(f"Daire oluşturuluyor: {daire_no_form}")
            daire_instance, daire_created = Daire.objects.get_or_create(
                blok=blok_instance,
                daire_no=daire_no_form,
                defaults={
                    'kullanici': user,
                    'telefon_no': telefon_no_form,
                    'blok': blok_instance,
                    'daire_no': daire_no_form
                }
            )
            print(f"Daire {'oluşturuldu' if daire_created else 'mevcut'}. ID: {daire_instance.id}")

            if not daire_created and not daire_instance.kullanici:
                daire_instance.kullanici = user
                daire_instance.telefon_no = telefon_no_form if telefon_no_form else daire_instance.telefon_no
                daire_instance.save()
                print("Kullanıcı mevcut daireye atandı")
            elif daire_created:
                 user.aktif_daire = daire_instance
                 user.save(update_fields=['aktif_daire'])
                 print("Kullanıcıya yeni daire aktif daire olarak atandı")
            
            if not user.aktif_daire and daire_instance.kullanici == user:
                 user.aktif_daire = daire_instance
                 user.save(update_fields=['aktif_daire'])
                 print("Kullanıcıya mevcut daire aktif daire olarak atandı")

            print("---------- KAYIT FORM SAVE TAMAMLANDI ----------")
        return user

class SiteAyarForm(forms.ModelForm):
    """
    Site ayarlarını güncellemek için form.
    Form for updating site settings.
    """
    class Meta:
        model = Site
        fields = [
            'ad', 'adres', 'yonetici_adi', 'yonetici_email',
            'aidat_miktari', 'gecikme_faizi_orani', 'son_odeme_gunu_oncesi_hatirlatma',
            'otomatik_mail_aktif', 'makbuz_yukleme_aktif',
            'logo', 'duyurular', 'site_kurallari'
        ]
        widgets = {
            'ad': forms.TextInput(attrs={'class': 'form-control'}),
            'adres': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'yonetici_adi': forms.TextInput(attrs={'class': 'form-control'}),
            'yonetici_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'aidat_miktari': forms.NumberInput(attrs={'class': 'form-control'}),
            'gecikme_faizi_orani': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'duyurular': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'site_kurallari': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            # Checkbox'lar için özel stil gerekirse template'te ayarlanabilir
            # If custom styling is needed for checkboxes, it can be set in the template
        }
        help_texts = {
            'gecikme_faizi_orani': "Örn: 0.05 (yani %5). Geciken aidatlar için günlük uygulanacak faiz oranı.",
            'son_odeme_gunu_oncesi_hatirlatma': "Aidat son ödeme gününden kaç gün önce hatırlatma maili gönderilsin? (0 pasif yapar)",
            'otomatik_mail_aktif': "Yeni kayıt, aidat hatırlatma gibi durumlar için otomatik mail gönderimi aktif edilsin mi?",
            'makbuz_yukleme_aktif': "Kullanıcıların aidat ödemesi yaparken makbuz yüklemesine izin verilsin mi?",
            'logo': "Sitenizin logosu. Panelde ve raporlarda kullanılabilir."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Checkbox'lara form-check-input class'ını ekle
        # Add form-check-input class to checkboxes
        if 'otomatik_mail_aktif' in self.fields:
            self.fields['otomatik_mail_aktif'].widget.attrs.update({'class': 'form-check-input'})
        if 'makbuz_yukleme_aktif' in self.fields:
            self.fields['makbuz_yukleme_aktif'].widget.attrs.update({'class': 'form-check-input'}) 

class DaireForm(forms.ModelForm):
    """
    Form for creating and updating Daire records.
    Daire kayıtları oluşturmak ve güncellemek için form.
    """
    def __init__(self, *args, **kwargs):
        site = kwargs.pop('site', None)
        super().__init__(*args, **kwargs)

        # Alanlara Bootstrap sınıflarını ata
        # Assign Bootstrap classes to fields
        self.fields['blok'].widget.attrs.update({'class': 'form-select form-control-sm'})
        self.fields['daire_no'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['daire_tipi'].widget.attrs.update({'class': 'form-select form-control-sm'})
        self.fields['kullanici'].widget.attrs.update({'class': 'form-select form-control-sm'})
        self.fields['telefon_no'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['m2_brut'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['m2_net'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['devir_bakiye_gecen_yil'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['devir_bakiye_yili'].widget.attrs.update({'class': 'form-control form-control-sm', 'type': 'number', 'placeholder': 'YYYY'})
        self.fields['aciklama'].widget.attrs.update({'class': 'form-control form-control-sm', 'rows': 3})
        self.fields['is_dolu'].widget.attrs.update({'class': 'form-check-input'}) # Bootstrap 5 için

        # Blokları siteye göre filtrele
        # Filter blocks by site
        if site:
            self.fields['blok'].queryset = Blok.objects.filter(site=site).order_by('ad')
        elif self.instance and self.instance.pk and self.instance.blok:
            # Eğer form bir instance ile başlatıldıysa ve site verilmediyse, instance'ın sitesini kullan
            # If the form is initialized with an instance and no site is provided, use the instance's site
            self.fields['blok'].queryset = Blok.objects.filter(site=self.instance.blok.site).order_by('ad')
        else:
            self.fields['blok'].queryset = Blok.objects.none()

        # Kullanıcıları (sakinleri) siteye göre filtrele (opsiyonel, eğer tüm kullanıcılar listeleniyorsa)
        # Filter users (residents) by site (optional, if all users are listed)
        # Şimdilik tüm kullanıcıları listeliyoruz, ancak ileride site_kodu eşleşenler veya is_sakin=True olanlar filtrelenebilir.
        # For now, we list all users, but in the future, those matching site_code or is_sakin=True can be filtered.
        self.fields['kullanici'].queryset = Kullanici.objects.all().order_by('first_name', 'last_name')
        self.fields['kullanici'].required = False # Sakin atanmamış daireler olabilir
        self.fields['telefon_no'].required = False
        self.fields['m2_brut'].required = False
        self.fields['m2_net'].required = False
        self.fields['devir_bakiye_gecen_yil'].required = False
        self.fields['devir_bakiye_yili'].required = False
        self.fields['aciklama'].required = False

    class Meta:
        model = Daire
        fields = [
            'blok', 'daire_no', 'daire_tipi', 'kullanici', 'telefon_no',
            'm2_brut', 'm2_net', 'is_dolu',
            'devir_bakiye_gecen_yil', 'devir_bakiye_yili', 'aciklama'
        ]
        widgets = {
            'devir_bakiye_yili': forms.NumberInput(attrs={'placeholder': 'YYYY'}),
        } 

class BlokYonetimForm(forms.ModelForm):
    """
    Blok yönetimi için form.
    Form for block management.
    """
    daire_sayisi = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Bloktaki daire sayısı'
        }),
        help_text='Bloktaki toplam daire sayısı (opsiyonel)'
    )

    class Meta:
        model = Blok
        fields = ['ad', 'aidat_miktari', 'aciklama']
        widgets = {
            'ad': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Örn: A Blok'
            }),
            'aidat_miktari': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Blok için özel aidat miktarı'
            }),
            'aciklama': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 3,
                'placeholder': 'Blok hakkında ek bilgiler'
            })
        }
        help_texts = {
            'aidat_miktari': 'Bu blok için özel aidat miktarı. Boş bırakılırsa site genel aidat miktarı kullanılır.',
            'aciklama': 'Blok hakkında ek bilgiler (opsiyonel)'
        }

    def __init__(self, *args, **kwargs):
        self.site = kwargs.pop('site', None)
        super().__init__(*args, **kwargs)
        
        # Site genel aidat miktarını göster
        # Show site's general aidat amount
        if self.site and self.site.aidat_miktari:
            self.fields['aidat_miktari'].help_text += f" (Site genel aidat miktarı: {self.site.aidat_miktari} TL)"

    def clean_ad(self):
        """
        Blok adını büyük harfe çevir ve benzersizliğini kontrol et
        Convert block name to uppercase and check uniqueness
        """
        ad = self.cleaned_data.get('ad', '').strip().upper()
        if not ad:
            raise forms.ValidationError("Blok adı gereklidir.")
        
        # Aynı site içinde aynı blok adı var mı kontrol et
        # Check if same block name exists in the same site
        if self.site and Blok.objects.filter(site=self.site, ad=ad).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError(f"'{ad}' bloğu bu site için zaten mevcut.")
        
        return ad

    def clean_aidat_miktari(self):
        """
        Aidat miktarını kontrol et
        Check aidat amount
        """
        aidat = self.cleaned_data.get('aidat_miktari')
        if aidat is not None and aidat <= 0:
            raise forms.ValidationError("Aidat miktarı 0'dan büyük olmalıdır.")
        return aidat 