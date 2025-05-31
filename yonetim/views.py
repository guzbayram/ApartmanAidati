from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.db import transaction
from django.db.models import Sum, Q, Count, F, ExpressionWrapper, DecimalField, Value, CharField, IntegerField
from django.db.models.functions import Coalesce, Cast
from django.utils import timezone
from django.urls import reverse, reverse_lazy
import datetime
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django import forms
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

# Model Imports
from .models import Kullanici, Site, Blok, Daire, Aidat, Gider, YillikRaporPDF

# Form Imports
from .forms import AidatForm, GiderForm, KullaniciGirisForm, KullaniciKayitForm, SiteAyarForm, DaireForm, BlokYonetimForm
# Henüz oluşturulmadı, eklenecekler:
# from .forms import KullaniciKayitForm, SiteForm, KullaniciGirisForm, DaireForm, YillikRaporForm

# Utils / Helper Functions
from .utils import get_user_site, get_user_daire # daire_natural_sort_key artık kullanılmayabiliriz

# --- Helper Functions (Bazılarını buraya taşıyabilir veya utils.py oluşturabiliriz) ---

# --- Authentication Views --- 
def giris_view(request):
    """
    Kullanıcı girişi için view.
    View for user login.
    """
    if request.user.is_authenticated:
        return redirect('yonetim:panel')

    if request.method == 'POST':
        print("---------- KAYIT FORM POST DATA ----------")
        print(request.POST) # POST verisini konsola yazdır
        form = KullaniciGirisForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            site_kodu = form.cleaned_data.get('site_kodu')
            password = form.cleaned_data.get('password')
            
            try:
                user = Kullanici.objects.get(username=username, site_kodu=site_kodu)
                if not password:  # Şifre boşsa direkt giriş yap
                    login(request, user)
                    messages.success(request, f"Hoş geldiniz, {user.get_full_name() or user.username}!")
                    return redirect('yonetim:panel')
                else:  # Şifre varsa normal authentication
                    user = authenticate(request, username=username, password=password)
                    if user is not None:
                        login(request, user)
                        messages.success(request, f"Hoş geldiniz, {user.get_full_name() or user.username}!")
                        return redirect('yonetim:panel')
                    else:
                        messages.error(request, "Şifre hatalı.")
            except Kullanici.DoesNotExist:
                messages.error(request, "Kullanıcı adı veya site kodu hatalı.")
    else:
        form = KullaniciGirisForm()
    
    return render(request, 'yonetim/giris.html', {'form': form})

def kayit_view(request):
    if request.user.is_authenticated:
        return redirect('yonetim:panel')

    if request.method == 'POST':
        print("---------- KAYIT FORM POST DATA ----------")
        print(request.POST) # POST verisini konsola yazdır
        form = KullaniciKayitForm(request.POST)
        if form.is_valid():
            try:
                user = form.save() # Metod adını formdaki gibi 'save' olarak düzelttik.
                print(f"---------- KAYIT BAŞARILI ----------")
                print(f"Kullanıcı adı: {user.username}")
                print(f"Site kodu: {user.site_kodu}")
                print(f"Şifre durumu: {'Şifre var' if user.has_usable_password() else 'Şifre yok'}")
                
                # Kullanıcıyı otomatik olarak giriş yap
                login(request, user)
                messages.success(request, "Kaydınız başarıyla oluşturuldu ve giriş yaptınız!")
                return redirect(reverse_lazy('yonetim:panel'))
            except forms.ValidationError as e:
                print(f"---------- KAYIT VALIDATION HATASI ----------")
                print(str(e))
                messages.error(request, f"Kayıt sırasında bir doğrulama hatası oluştu: {e}")
            except Exception as e:
                print(f"---------- KAYIT HATASI ----------")
                print(str(e))
                import traceback
                traceback.print_exc()
                messages.error(request, f"Kayıt sırasında beklenmedik bir hata oluştu. Lütfen tekrar deneyin veya yöneticiyle iletişime geçin. Detay: {e}")
        else:
            print("---------- KAYIT FORM HATALARI ----------")
            print(form.errors.as_json(escape_html=True))
            error_message = "Formda hatalar var. Lütfen tüm alanları doğru girdiğinizden emin olun."
            if form.non_field_errors():
                error_message += " Genel Hatalar: " + " ".join(form.non_field_errors())
            for field, errors in form.errors.items():
                error_message += f" Alan '{form.fields[field].label or field}': " + " ".join(errors)
            messages.error(request, error_message)
    else:
        form = KullaniciKayitForm()
    
    return render(request, 'yonetim/kayit.html', {'form': form, 'title': 'Kayıt Ol'})

def cikis_view(request):
    logout(request)
    messages.info(request, "Başarıyla çıkış yaptınız.") # info veya success kullanılabilir.
    return redirect('yonetim:giris')

# --- Main Panel View --- 
@login_required
def panel_view(request):
    # print("--- PANEL_VIEW BAŞLANGIÇ ---") # Debug için
    if not request.user.is_authenticated:
        messages.warning(request, "Bu sayfayı görüntülemek için giriş yapmalısınız.")
        return redirect('yonetim:giris')

    user = request.user
    # user_site ve user_daire başlangıçta None olacak, aşağıda belirlenecek
    # user_site and user_daire will be None initially, determined below
    user_site = None
    user_daire = None

    # Context sözlüğünü burada, if user_site kontrolünden önce başlatıyoruz
    # We initialize the context dictionary here, before the if user_site check
    context = {
        'user': user,
        'user_site': None, # Başlangıçta None
        'user_daire': None, # Başlangıçta None
        'aidat_form': None,
        'gider_form': None,
        'site_daireleri_ozet': [],
        'toplam_gelir': Decimal('0.00'),
        'toplam_gider': Decimal('0.00'),
        'kasa_bakiyesi': Decimal('0.00'),
        'current_year': timezone.now().year,
        'all_aidatlar_list': [],
        'all_giderler_list': [],
        'is_admin': user.is_superuser, # Süper admin kontrolü
        'tum_siteler': None, # Süper admin için aşağıda belirlenecek
    }

    # user_site ve user_daire bilgisini al ve context'e ata
    # Get user_site and user_daire info and assign to context
    if not user.is_superuser:
        user_site = get_user_site(user) # Değişkene al
        user_daire = get_user_daire(user) # Değişkene al
        context['user_site'] = user_site # Context'e ata
        context['user_daire'] = user_daire # Context'e ata
    else:
        # Admin kullanıcısı için site seçimi / Site selection for admin
        tum_siteler_qs = Site.objects.all().order_by('ad')
        context['tum_siteler'] = list(tum_siteler_qs) # QuerySet'i listeye çevirip context'e ata

        if not tum_siteler_qs.exists():
            messages.warning(request, "Henüz hiç site kaydı bulunmuyor.")
            # user_site None kalacak, panelde uyarı gösterilecek
        else:
             site_id = request.GET.get('site_id')
             if site_id:
                 try:
                     user_site = Site.objects.get(id=site_id) # Değişkene al
                     context['user_site'] = user_site # Context'e ata
                 except Site.DoesNotExist:
                     messages.error(request, "Seçilen site bulunamadı.")
                     # user_site None kalacak, panelde uyarı gösterilecek
             else:
                 user_site = tum_siteler_qs.first() # Değişkene al
                 context['user_site'] = user_site # Context'e ata

    # Eğer user_site dolu ise veri çekme işlemlerini yap ve context'i güncelle
    # If user_site is not None, perform data fetching operations and update the context
    if user_site: 

        print("[DEBUG] ### user_site koşulu TRUE - Başlangıç ###") # Debugging için
        # Form başlatma try bloğu daha önce eklendi
        # The form initialization try block was added previously
        print("[DEBUG] Formlar initialize ediliyor...") # Debugging için
        try: # Form başlatma hatalarını yakalamak için try bloğu
            daire_id_for_form = user_daire.id if user_daire else None
            context['aidat_form'] = AidatForm(site=user_site, panel_form=True, daire_id=daire_id_for_form) # Context'i güncelle
            context['gider_form'] = GiderForm(site=user_site, panel_form=True) # Context'i güncelle
            print("[DEBUG] Formlar initialize edildi.") # Debugging için
        except Exception as e:
            print(f"[ERROR] Formlar initialize edilirken hata oluştu: {e}") # Hata durumunda yazdır
            import traceback
            traceback.print_exc()
            context['aidat_form'] = None # Hata durumunda formları None yap
            context['gider_form'] = None

        if request.method == 'POST':
            print("[DEBUG] POST isteği algılandı.") # Debugging için
            # POST işleme mantığı
            # ... (mevcut POST işleme kodu buraya gelecek veya taşınacak) ...
            # ÖNEMLİ: POST işleminden sonra redirect yapılmıyorsa, form hatalıysa aşağıdaki veri çekme kısmı çalışmalı.
            # IMPORTANT: If no redirect after POST, the data fetching part below should run if the form is invalid.
            # Şu anki kod yapınızda POST başarısız olursa redirect yapılmıyor, bu doğru.
            # In your current code structure, if POST fails, no redirect is done, which is correct.
            
            # Aidat ekleme işlemi
            if 'submit_aidat' in request.POST:
                if user_daire or user.is_superuser:  # Admin her daireye aidat ekleyebilir
                    form_aidat_instance = AidatForm(request.POST, request.FILES, site=user_site, daire_id=user_daire.id if user_daire else None, panel_form=True)
                    if form_aidat_instance.is_valid():
                        try:
                            aidat = form_aidat_instance.save(commit=False)
                            if user_daire: # Kullanıcı kendi dairesine ekliyorsa daireyi atar
                                aidat.daire = user_daire
                            # Admin her daireye ekleyebilir, bu durumda formdaki daire alanı kullanılacak
                            # Admin can add to any flat, in this case the flat field in the form will be used
                            if not aidat.tarih:
                                aidat.tarih = timezone.now().date()
                            aidat.save()
                            messages.success(request, f"{aidat.daire.daire_tam_adi if aidat.daire else 'Seçilen daire'} için aidat başarıyla eklendi.")
                            context['last_submitted_form'] = 'aidat' # Son gönderilen formu context'e ekle
                            # POST başarılı olunca redirect yapılıyor, bu satır aslında redirect sonrası tekrar çalışmayacak
                            # Redirect is done after successful POST, this line will not actually run after redirect
                        except Exception as e:
                            print("--- AIDAT KAYDETME HATASI DETAYI ---")
                            import traceback
                            traceback.print_exc()
                            messages.error(request, f"Aidat eklenirken bir hata oluştu: {e} (Detaylar konsolda)")
                            context['aidat_form'] = form_aidat_instance # Hatalı formu context'e geri gönder
                            context['last_submitted_form'] = 'aidat' # Son gönderilen formu context'e ekle
                    else:
                        context['aidat_form'] = form_aidat_instance # Hatalı formu context'e geri gönder
                        print("--- AİDAT FORMU HATALARI ---")
                        print(context['aidat_form'].errors.as_json(escape_html=True))
                        messages.error(request, f"Aidat formu geçerli değil. Lütfen hataları kontrol edin: {context['aidat_form'].errors.as_text()}")
                        context['last_submitted_form'] = 'aidat' # Son gönderilen formu context'e ekle


            # Gider ekleme işlemi
            elif 'submit_gider' in request.POST and (user.is_yonetici or user.is_superuser):
                form_gider_instance = GiderForm(request.POST, request.FILES, site=user_site, panel_form=True)
                if form_gider_instance.is_valid():
                    try:
                        gider = form_gider_instance.save(commit=False)
                        gider.site = user_site
                        if not gider.tarih:
                            gider.tarih = timezone.now().date()
                        gider.save()
                        messages.success(request, "Gider başarıyla eklendi.")
                        context['last_submitted_form'] = 'gider' # Son gönderilen formu context'e ekle
                        # POST başarılı olunca redirect yapılıyor, bu satır aslında redirect sonrası tekrar çalışmayacak
                        # Redirect is done after successful POST, this line will not actually run after redirect
                    except Exception as e:
                        messages.error(request, f"Gider eklenirken bir hata oluştu: {e}")
                        context['gider_form'] = form_gider_instance # Hatalı formu context'e geri gönder
                        context['last_submitted_form'] = 'gider' # Son gönderilen formu context'e ekle
                else:
                    context['gider_form'] = form_gider_instance # Hatalı formu context'e geri gönder
                    messages.error(request, f"Gider formu geçerli değil. Lütfen hataları kontrol edin: {context['gider_form'].errors.as_text()}")
                    context['last_submitted_form'] = 'gider' # Son gönderilen formu context'e ekle


        # POST işleme mantığı bittiğinde veya GET isteği ise buraya gelir
        # Reached here after POST logic or for GET request
        print("[DEBUG] Veri çekme kısmına geçiliyor...") # Debugging için

        # --- Veri çekme ve listeleri hazırlama kısımları (Try blokları ile) ---
        # --- Data fetching and list preparation parts (with Try blocks) ---

        # Daire Özetleri
        print("[DEBUG] Daire Özetleri hazırlanıyor...") # Debugging için
        try: # Daire özeti hazırlama hatalarını yakalamak için try bloğu
            all_site_daireleri = Daire.objects.filter(blok__site=user_site).select_related('blok', 'kullanici')
            print(f"[DEBUG QUERY] all_site_daireleri count after query: {all_site_daireleri.count()}") # Debugging için QuerySet sonuç sayısı

            site_daireleri_ozet_listesi = [] # Geçici liste
            user_daire_ozet_item = None

            for daire in all_site_daireleri:
                # Hesaplamalar için gerekli verileri çek
                aidatlar_qs = Aidat.objects.filter(daire=daire)
                toplam_aidat = aidatlar_qs.aggregate(toplam=Coalesce(Sum('tutar'), Decimal('0.00')))['toplam']
                son_odeme = aidatlar_qs.order_by('-tarih').first()
                
                # Yıllık borç hesaplama (Basit Örnek: Site Genel Aidatı * 12 veya Blok Aidatı * 12)
                # Annual debt calculation (Simple Example: Site General Due * 12 or Block Due * 12)
                # Daha karmaşık aidat senaryoları için bu kısım güncellenmeli
                # For more complex due scenarios, this part should be updated
                aidat_miktari = daire.blok.aidat_miktari if daire.blok.aidat_miktari is not None else user_site.aidat_miktari
                yillik_borc = (aidat_miktari * 12) if aidat_miktari is not None else Decimal('0.00')
                
                odenen_tutar = toplam_aidat # Şimdilik tüm ödenenleri alıyoruz
                kalan_borc = yillik_borc - odenen_tutar # Basit kalan borç hesaplama
                # Devir bakiye de bu hesaba katılmalı
                # Carry-over balance should also be included in this calculation
                kalan_borc += daire.devir_bakiye_gecen_yil # Devir bakiyeyi ekle


                ozet_item = {
                    'daire': daire,
                    'toplam_aidat': toplam_aidat, # Hesaplandı
                    'son_odeme': son_odeme, # Hesaplandı
                    'yillik_borc': yillik_borc, # Hesaplandı
                    'odenen_tutar': odenen_tutar, # Hesaplandı
                    'kalan_borc': kalan_borc, # Hesaplandı
                }

                if user_daire and daire.id == user_daire.id: # Eğer kullanıcının dairesiyse
                    user_daire_ozet_item = ozet_item
                else:
                    site_daireleri_ozet_listesi.append(ozet_item)

            # Diğer daireleri blok ve daire numarasına göre sırala
            # Sort other flats by block and flat number
            # Daire modeli zaten 'blok', 'daire_no'ya göre sıralı geliyor, ama emin olalım
            # Daire natural sort key kullanarak daha doğru sıralama yapılabilir
            # Flats come already sorted by 'block', 'flat_no', but let's make sure
            # More accurate sorting can be done using Daire natural sort key

            # Eğer user_daire_ozet varsa, listeye ilk onu ekle
            # If user_daire_ozet exists, add it first to the list
            if user_daire_ozet_item:
                context['site_daireleri_ozet'].append(user_daire_ozet_item) # Context'e ekle

            # Kalan daireleri mevcut sıralamasıyla ekle (model meta ordering)
            # Add remaining flats with their existing order (model meta ordering)
            context['site_daireleri_ozet'].extend(site_daireleri_ozet_listesi) # Context'e ekle
            print(f"[DEBUG] site_daireleri_ozet count after processing: {len(context['site_daireleri_ozet'])}") # Debugging için list count
            print("[DEBUG] Daire Özetleri hazırlandı.") # Debugging için

        except Exception as e:
            print(f"[ERROR] Daire Özetleri Hazırlanırken Hata: {e}") # Hata durumunda yazdır
            import traceback
            traceback.print_exc()
            context['site_daireleri_ozet'] = [] # Hata durumunda boş listeye ata


        # --- Tüm Aidat Kayıtları Verisini Hazırlama (Kullanıcı Dairesi Aidatları En Üstte) ---
        # --- Preparing All Dues Records Data (User's Flat Dues at the Top) ---
        print("[DEBUG] Aidat Listesi hazırlanıyor...") # Debugging için
        try: # Aidat listesi hazırlama hatalarını yakalamak için try bloğu
            all_aidatlar_for_site_qs = Aidat.objects.filter(daire__blok__site=user_site).select_related('daire', 'daire__blok') # QuerySet
            print(f"[DEBUG QUERY] all_aidatlar_for_site count after query: {all_aidatlar_for_site_qs.count()}") # Debugging için QuerySet sonuç sayısı

            user_aidatlar_listesi = [] # Geçici liste
            other_aidatlar_listesi = [] # Geçici liste

            if user_daire: # Eğer kullanıcının dairesi varsa
                 user_aidatlar_listesi = list(all_aidatlar_for_site_qs.filter(daire=user_daire).order_by('-tarih', '-id')) # Listeye çevir
                 other_aidatlar_listesi = list(all_aidatlar_for_site_qs.exclude(daire=user_daire).order_by('daire__blok__ad', 'daire__daire_no', '-tarih', '-id')) # Listeye çevir
            else: # Kullanıcının dairesi yoksa, tüm aidatları sadece daireye göre sırala
                 other_aidatlar_listesi = list(all_aidatlar_for_site_qs.order_by('daire__blok__ad', 'daire__daire_no', '-tarih', '-id')) # Listeye çevir
                 
            context['all_aidatlar_list'] = user_aidatlar_listesi + other_aidatlar_listesi # Context'e ata
            print(f"[DEBUG] all_aidatlar_list count after processing: {len(context['all_aidatlar_list'])}") # Debugging için list count
            print("[DEBUG] Aidat Listesi hazırlandı.") # Debugging için

        except Exception as e:
            print(f"[ERROR] Aidat Listesi Hazırlanırken Hata: {e}") # Hata durumunda yazdır
            import traceback
            traceback.print_exc()
            context['all_aidatlar_list'] = [] # Hata durumunda boş listeye ata


        # --- Tüm Gider Kayıtları Verisini Hazırlama ---
        # --- Preparing All Expense Records Data ---
        print("[DEBUG] Gider Listesi hazırlanıyor...") # Debugging için
        try: # Gider listesi hazırlama hatalarını yakalamak için try bloğu
            # Giderler daireye bağlı değil, sadece siteye bağlı, bu yüzden özel sıralama yok
            # Expenses are not linked to flat, only site, so no special sorting
            all_giderler_list_qs = Gider.objects.filter(site=user_site).order_by('-tarih', '-id') # QuerySet
            print(f"[DEBUG QUERY] all_giderler_list count after query: {all_giderler_list_qs.count()}") # Debugging için QuerySet sonuç sayısı
            context['all_giderler_list'] = list(all_giderler_list_qs) # Listeye çevirip context'e ata
            print(f"[DEBUG] all_giderler_list count after processing: {len(context['all_giderler_list'])}") # Debugging için list count
            print("[DEBUG] Gider Listesi hazırlandı.") # Debugging için

        except Exception as e:
            print(f"[ERROR] Gider Listesi Hazırlanırken Hata: {e}") # Hata durumunda yazdır
            import traceback
            traceback.print_exc()
            context['all_giderler_list'] = [] # Hata durumunda boş listeye ata


        # Finansal Özetler (Toplam gelir/gider/kasa bakiye) - Bu hesaplamalar zaten site bazında olduğu için değişmesine gerek yok
        # Financial Summaries (Total income/expense/cash balance) - These calculations are already site-based, no need to change
        print("[DEBUG] Finansal Özetler hazırlanıyor...") # Debugging için
        try: # Finansal özet hazırlama hatalarını yakalamak için try bloğu
            toplam_gelir_data = Aidat.objects.filter(daire__blok__site=user_site).aggregate(toplam=Coalesce(Sum('tutar'), Decimal('0.00')))
            context['toplam_gelir'] = toplam_gelir_data['toplam'] # Context'i güncelle

            toplam_gider_data = Gider.objects.filter(site=user_site).aggregate(toplam=Coalesce(Sum('tutar'), Decimal('0.00')))
            context['toplam_gider'] = toplam_gider_data['toplam'] # Context'i güncelle

            context['kasa_bakiyesi'] = context['toplam_gelir'] - context['toplam_gider'] # Context'i güncelle
            print(f"[DEBUG] Finansal Özetler - Gelir: {context['toplam_gelir']}, Gider: {context['toplam_gider']}, Kasa: {context['kasa_bakiyesi']}") # Debugging için
            print("[DEBUG] Finansal Özetler hazırlandı.") # Debugging için

        except Exception as e:
            print(f"[ERROR] Finansal Özetler Hazırlanırken Hata: {e}") # Hata durumunda yazdır
            import traceback
            traceback.print_exc()
            # Hata durumunda context'teki değerler başlangıçtaki varsayılan değerler olarak kalır
            # In case of error, the values in context remain the initial default values

        print("[DEBUG] ### user_site koşulu TRUE - Bitiş ###") # Debugging için

    # Eğer user.is_authenticated ve !user_site ise, panel.html içinde uygun mesaj gösterilir
    # If user.is_authenticated and !user_site, appropriate message is shown within panel.html
    # Eğer !user.is_authenticated ise, base.html şablonu giriş yapma linkini gösterecektir
    # If !user.is_authenticated, base.html template will show login link

    # context sözlüğü zaten tanımlı ve güncellendi
    # context dictionary is already defined and updated

    print(f"[DEBUG FINAL] all_aidatlar_list count in context: {len(context.get('all_aidatlar_list', []))}") # Debugging için final count
    print(f"[DEBUG FINAL] all_giderler_list count in context: {len(context.get('all_giderler_list', []))}") # Debugging için final count

    return render(request, 'yonetim/panel.html', context)

# --- Site Management Views --- 
@login_required
# @staff_member_required # Sadece staff kullanıcılar (genellikle yöneticiler) erişebilir
def site_bilgi_view(request):
    user = request.user
    user_site = get_user_site(user)

    if not user_site:
        messages.error(request, "Yönetilecek bir site bulunamadı veya site ile ilişkili değilsiniz.")
        return redirect('yonetim:panel') # Ya da başka bir uygun sayfaya yönlendir

    # Sadece site yöneticisi veya süper kullanıcı bu sayfaya erişebilmeli
    # Only the site manager or superuser should be able to access this page
    if not (user.is_yonetici or user.is_superuser):
        messages.warning(request, "Bu sayfayı görüntüleme yetkiniz yok.")
        return redirect('yonetim:panel')

    if request.method == 'POST':
        form = SiteAyarForm(request.POST, request.FILES, instance=user_site)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Site bilgileri başarıyla güncellendi.")
                return redirect('yonetim:site_bilgi') # Başarılı güncelleme sonrası aynı sayfaya yönlendir
            except Exception as e:
                messages.error(request, f"Site bilgileri güncellenirken bir hata oluştu: {e}")
        else:
            messages.warning(request, "Lütfen formdaki hataları düzeltin.")
    else:
        form = SiteAyarForm(instance=user_site)

    context = {
        'title': f'{user_site.ad} - Site Ayarları',
        'form': form,
        'user_site': user_site
    }
    return render(request, 'yonetim/site_bilgi.html', context)

# --- Blok, Daire, Aidat, Gider CRUD Views (İskeletler) --- 
@login_required
def blok_yonetimi_view(request):
    # TODO: Blok listeleme, ekleme, düzenleme, silme
    # List, add, edit, delete Blocks
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')
    # ... (BlokForm kullanılacak)
    context = {'title': 'Blok Yönetimi', 'user_site': user_site}
    return render(request, 'yonetim/placeholder_crud.html', context) # Geçici template

@login_required
def daire_yonetimi_view(request, blok_id=None):
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')

    # Blokları ve daireleri filtrelemek için
    # For filtering blocks and flats
    bloklar = Blok.objects.filter(site=user_site).order_by('ad')
    secili_blok = None
    daireler = Daire.objects.filter(blok__site=user_site).select_related('blok', 'kullanici').order_by('blok__ad', 'daire_no') # Başlangıçta tüm daireler

    if blok_id:
        try:
            secili_blok = Blok.objects.get(id=blok_id, site=user_site)
            daireler = daireler.filter(blok=secili_blok)
        except Blok.DoesNotExist:
            messages.error(request, "Belirtilen blok bulunamadı.")
            return redirect('yonetim:daire_yonetimi') # Blok ID'siz URL'ye yönlendir

    # Daire Ekleme/Düzenleme Formu
    # Flat Add/Edit Form
    # 'daire_id' URL'den gelirse düzenleme modunda olabiliriz, şimdilik sadece ekleme
    # If 'flat_id' comes from URL, we might be in edit mode, for now just add
    if request.method == 'POST':
        form = DaireForm(request.POST, site=user_site)
        if form.is_valid():
            try:
                yeni_daire = form.save(commit=False)
                # Formda blok zaten siteye göre filtrelendiği için site atamasına gerek yok.
                # Since the block in the form is already filtered by site, no need to assign site.
                yeni_daire.save()
                messages.success(request, f"{yeni_daire.daire_tam_adi} başarıyla eklendi.")
                # Eğer belirli bir blok seçiliyse o blok ID'si ile, değilse genel listeye yönlendir
                # Redirect to that block ID if a specific block is selected, otherwise to the general list
                if secili_blok:
                    return redirect('yonetim:daire_yonetimi_blok', blok_id=secili_blok.id)
                return redirect('yonetim:daire_yonetimi')
            except Exception as e:
                messages.error(request, f"Daire eklenirken bir hata oluştu: {e}")
        else:
            messages.warning(request, "Lütfen formdaki hataları düzeltin.")
    else:
        form = DaireForm(site=user_site)

    context = {
        'title': 'Daire Yönetimi',
        'user_site': user_site,
        'bloklar': bloklar,
        'secili_blok': secili_blok,
        'daireler': daireler,
        'form': form,
        'form_title': 'Yeni Daire Ekle' # Daha sonra düzenleme için değişebilir
    }
    # Geçici template yerine yeni bir template kullanacağız
    # We will use a new template instead of the temporary one
    return render(request, 'yonetim/daire_yonetimi.html', context)

@login_required
def aidat_yonetimi_view(request, daire_id=None):
    """
    Aidat yönetimi için view.
    View for due management.
    Hem genel aidat listesi hem de daireye özel aidat listesi için kullanılır.
    Used for both general due list and flat-specific due list.
    """
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')

    # Daire ID'si varsa o dairenin aidatlarını, yoksa tüm aidatları getir
    # If daire_id exists, get that flat's dues, otherwise get all dues
    aidatlar_qs = Aidat.objects.filter(daire__blok__site=user_site).select_related('daire', 'daire__blok')
    secili_daire = None

    if daire_id:
        try:
            secili_daire = Daire.objects.get(id=daire_id, blok__site=user_site)
            aidatlar_qs = aidatlar_qs.filter(daire=secili_daire)
        except Daire.DoesNotExist:
            messages.error(request, "Belirtilen daire bulunamadı.")
            return redirect('yonetim:aidat_yonetimi')

    # Aidatları tarihe göre sırala
    # Sort dues by date
    aidatlar_qs = aidatlar_qs.order_by('-tarih', '-id')

    # Toplam tutarı hesapla
    # Calculate total amount
    toplam_tutar = aidatlar_qs.aggregate(toplam=Sum('tutar'))['toplam'] or 0

    context = {
        'title': f'Aidat Yönetimi - {secili_daire.daire_tam_adi if secili_daire else "Tüm Aidatlar"}',
        'user_site': user_site,
        'aidatlar': aidatlar_qs,
        'secili_daire': secili_daire,
        'toplam_tutar': toplam_tutar,  # Toplam tutarı context'e ekle
    }
    return render(request, 'yonetim/aidat_yonetimi.html', context)

@login_required
def gider_yonetimi_view(request):
    # TODO: Gider listeleme, ekleme, düzenleme, silme (yöneticiler için)
    # List, add, edit, delete Expenses (for managers)
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')
    # ... (GiderForm kullanılacak)
    context = {'title': 'Gider Yönetimi', 'user_site': user_site}
    return render(request, 'yonetim/placeholder_crud.html', context) # Geçici template

@login_required
def kullanici_yonetimi_view(request):
    # TODO: Kullanıcı listeleme, rollerini düzenleme (yönetici atama/çıkarma), daire atama
    # List users, edit roles (assign/remove manager), assign flat
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')
    # ... (Özel formlar veya Django admin benzeri bir arayüz gerekebilir)
    # Custom forms or a Django admin-like interface might be needed
    context = {'title': 'Kullanıcı Yönetimi', 'user_site': user_site}
    return render(request, 'yonetim/placeholder_crud.html', context) # Geçici template

# --- Reporting and Utility Views (İskeletler) --- 
@login_required
def yillik_rapor_pdf_view(request, yil=None):
    # TODO: Yıllık gelir-gider raporu, aidat ödeme durumları (PDF formatında)
    # Annual income-expense report, due payment statuses (in PDF format)
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')
    # ... (PDF oluşturma kütüphanesi kullanılacak, örn: ReportLab, WeasyPrint)
    # PDF generation library will be used, e.g., ReportLab, WeasyPrint
    if not yil: yil = timezone.now().year
    context = {'title': f'{yil} Yıllık Rapor', 'user_site': user_site, 'yil': yil}
    # return HttpResponse("PDF Raporu burada olacak", content_type='application/pdf')
    return render(request, 'yonetim/placeholder_report.html', context) # Geçici template

@login_required
def aylik_rapor_view(request, yil=None, ay=None):
    # TODO: Aylık detaylı gelir-gider, aidat ödemeleri (HTML veya Excel)
    # Detailed monthly income-expense, due payments (HTML or Excel)
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')
    # ...
    now = timezone.now()
    if not yil: yil = now.year
    if not ay: ay = now.month
    context = {'title': f'{yil}-{ay:02d} Aylık Rapor', 'user_site': user_site, 'yil': yil, 'ay': ay}
    return render(request, 'yonetim/placeholder_report.html', context) # Geçici template

@login_required
def import_export_view(request):
    # TODO: Daire, sakin, aidat verisi import/export (Excel, CSV)
    # Import/export flat, resident, due data (Excel, CSV)
    user_site = get_user_site(request.user)
    if not user_site or not (request.user.is_yonetici or request.user.is_superuser):
        messages.warning(request, "Bu işlem için yetkiniz yok veya bir siteye bağlı değilsiniz.")
        return redirect('yonetim:panel')
    # ... (django-import-export kütüphanesi veya özel mantık)
    # django-import-export library or custom logic
    context = {'title': 'Veri Import/Export', 'user_site': user_site}
    return render(request, 'yonetim/placeholder_utils.html', context) # Geçici template

# --- AJAX Views (İskeletler) --- 
@login_required
def ajax_blok_getir(request):
    # TODO: Site seçildiğinde blokları getiren AJAX view (Kayıt formunda kullanılabilir)
    # AJAX view that fetches blocks when a site is selected (Can be used in Registration form)
    # ... (Jsonresponse dönecek)
    # Will return JsonResponse
    if not request.user.is_authenticated:
         return JsonResponse({'error': 'Yetkisiz erişim'}, status=401)
    site_id = request.GET.get('site_id')
    bloklar = []
    if site_id:
        try:
            site = Site.objects.get(pk=site_id)
            bloklar = list(Blok.objects.filter(site=site).values('id', 'ad'))
        except Site.DoesNotExist:
            return JsonResponse({'error': 'Site bulunamadı'}, status=404)
    return JsonResponse({'bloklar': bloklar})

@login_required
def ajax_daire_borc_sorgula(request):
    # TODO: Bir dairenin güncel borcunu sorgulayan AJAX view
    # AJAX view that queries the current debt of a flat
    # ... (Jsonresponse dönecek)
    # Will return JsonResponse
    if not request.user.is_authenticated:
         return JsonResponse({'error': 'Yetkisiz erişim'}, status=401)
    daire_id = request.GET.get('daire_id')
    # ... (borç hesaplama mantığı)
    # debt calculation logic
    # return JsonResponse({'borc': 0.00, 'daire_adi': 'Daire X'})
    return JsonResponse({'error': 'Henüz implemente edilmedi'}, status=501)

# Diğer view fonksiyonları buraya eklenebilir
# Other view functions can be added here

class BlokYonetimView(LoginRequiredMixin, View):
    """
    Blok yönetimi için view.
    View for block management.
    Hem liste, ekleme hem de düzenleme işlemlerini yönetir.
    Manages listing, adding, and editing operations.
    """
    template_name = 'yonetim/blok_yonetimi.html'

    def get(self, request, pk=None): # pk parametresi eklendi (varsayılan None)
        site = request.user.site_kodu
        if not site:
            messages.error(request, "Site kodu bulunamadı.")
            return redirect('yonetim:panel')

        try:
            site_obj = Site.objects.get(kod=site)
        except Site.DoesNotExist:
            messages.error(request, "Site bulunamadı.")
            return redirect('yonetim:panel')

        # Blokları ve her blok için dolu daire sayısını getir
        # Get blocks and count of occupied flats for each block
        bloklar = Blok.objects.filter(site=site_obj).annotate(
            dolu_daire_count=Count('daireler', filter=Q(daireler__is_dolu=True)),
            toplam_daire_sayisi=Count('daireler')
        ).order_by('ad')
        
        # Her blok için aidat miktarını belirle (blok özel aidatı varsa onu, yoksa site genel aidatını kullan)
        # Determine aidat amount for each block (use block specific aidat if exists, otherwise use site general aidat)
        for blok in bloklar:
            if blok.aidat_miktari is not None:
                blok.aidat_gosterim = f"{blok.aidat_miktari:.2f} TL"
            else:
                blok.aidat_gosterim = f"{site_obj.aidat_miktari:.2f} TL (Site Genel)"

        form_instance = None
        form_title = "Yeni Blok Ekle" # Form başlığı

        if pk: # Eğer pk varsa düzenleme modundayız
            try:
                # Belirtilen ID'deki bloğu getir (kullanıcının sitesine ait olduğundan emin ol)
                # Get the block with the specified ID (ensure it belongs to the user's site)
                blok_to_edit = get_object_or_404(Blok, pk=pk, site=site_obj)
                form_instance = BlokYonetimForm(instance=blok_to_edit, site=site_obj)
                form_title = f"'{blok_to_edit.ad}' Bloğunu Düzenle" # Başlığı güncelle

            except Http404:
                 messages.error(request, "Düzenlenmek istenen blok bulunamadı.")
                 return redirect('yonetim:blok_yonetimi') # Bulunamazsa ana blok yönetimine yönlendir
        else: # pk yoksa yeni ekleme modundayız
            form_instance = BlokYonetimForm(site=site_obj)

        context = {
            'site': site_obj,
            'bloklar': bloklar, # Artık her blok için dolu_daire_count, toplam_daire_sayisi ve aidat_gosterim bilgileri var
            'form': form_instance,
            'form_title': form_title,
            'site_genel_aidat': site_obj.aidat_miktari,
            'editing_blok_id': pk
        }
        return render(request, self.template_name, context)

    @transaction.atomic # İşlemleri tek bir transaction içinde yap
    def post(self, request, pk=None): # pk parametresi eklendi (varsayılan None)
        site = request.user.site_kodu
        if not site:
            messages.error(request, "Site kodu bulunamadı.")
            return redirect('yonetim:panel')

        try:
            site_obj = Site.objects.get(kod=site)
        except Site.DoesNotExist:
            messages.error(request, "Site bulunamadı.")
            return redirect('yonetim:panel')

        # Blok silme işlemi (mevcut kod olduğu gibi kalacak)
        if 'sil' in request.POST:
            blok_id = request.POST.get('blok_id')
            try:
                blok = Blok.objects.get(id=blok_id, site=site_obj)
                if blok.daireler.exists():
                    messages.error(request, f"'{blok.ad}' bloğunda daireler var. Önce daireleri silmelisiniz.")
                else:
                    blok.delete()
                    messages.success(request, f"'{blok.ad}' bloğu silindi.")
            except Blok.DoesNotExist:
                messages.error(request, "Blok bulunamadı.")
            # Silme işleminden sonra pk olsa bile her zaman ana listeye yönlendir
            return redirect('yonetim:blok_yonetimi')

        # Blok ekleme/düzenleme işlemi
        form_instance = None
        blok_instance = None

        if pk: # Eğer pk varsa düzenleme işlemi
             try:
                 blok_instance = get_object_or_404(Blok, pk=pk, site=site_obj)
                 form_instance = BlokYonetimForm(request.POST, instance=blok_instance, site=site_obj)
             except Http404:
                 messages.error(request, "Düzenlenmek istenen blok bulunamadı.")
                 return redirect('yonetim:blok_yonetimi')
        else: # pk yoksa yeni ekleme işlemi
             form_instance = BlokYonetimForm(request.POST, site=site_obj)

        if form_instance.is_valid():
            blok = form_instance.save(commit=False)
            blok.site = site_obj # Siteyi ata
            blok.save()

            # Formdaki daire sayısı bilgisini kullanarak daire oluşturma/güncelleme mantığı
            # Logic to create/update flats using the flat count from the form
            daire_sayisi_form = form_instance.cleaned_data.get('daire_sayisi')
            mevcut_daire_sayisi = blok.daireler.count()

            if daire_sayisi_form is not None and daire_sayisi_form > mevcut_daire_sayisi:
                 fark = daire_sayisi_form - mevcut_daire_sayisi
                 print(f"{blok.ad} bloğu için {fark} adet yeni daire oluşturuluyor.")
                 # Mevcut en yüksek daire numarasını bul
                 # Find the current highest flat number
                 son_numara = 0
                 try:
                     # Bloktaki mevcut daire numaralarını sayısal olarak sırala
                     # Numerically sort existing flat numbers in the block
                     en_yuksek_daire = blok.daireler.annotate(
                          num_int=ExpressionWrapper(
                              Cast('daire_no', IntegerField(strict=False)),
                              output_field=IntegerField()
                          )
                     ).order_by('-num_int').first()

                     if en_yuksek_daire and en_yuksek_daire.daire_no.isdigit():
                          son_numara = int(en_yuksek_daire.daire_no)
                     else:
                          # Eğer sayısal numara yoksa veya metin içeriyorsa mevcut sayıdan başla
                          # If there's no numeric number or it contains text, start from the current count
                           son_numara = mevcut_daire_sayisi

                 except (ValueError, TypeError):
                      son_numara = mevcut_daire_sayisi

                 for i in range(fark):
                      yeni_daire_no = str(son_numara + i + 1)

                      # Daire numarası zaten var mı kontrol et (tekrarlamayı önlemek için)
                      # Check if the flat number already exists (to prevent duplication)
                      if not Daire.objects.filter(blok=blok, daire_no=yeni_daire_no).exists():
                           Daire.objects.create(
                                blok=blok,
                                daire_no=yeni_daire_no,
                                is_dolu=False, # Yeni daire varsayılan olarak boş
                                # Diğer alanlar (kullanici, telefon, tip, m2 vb.) boş kalabilir
                           )
                           print(f"  - Yeni daire oluşturuldu: {blok.ad} - Daire {yeni_daire_no}")
                      else:
                           print(f"  - Daire numarası {yeni_daire_no} zaten mevcut, atlanıyor.")


            # Eğer daire sayısı formdaki sayıdan fazlaysa (silme durumu), burada herhangi bir işlem yapmıyoruz.
            # If the flat count is more than the number in the form (deletion case), we do nothing here.
            # Daire silme işlemi Daire Yönetimi ekranında yapılmalı veya ayrı bir onay süreci olmalı.
            # Flat deletion should be done in the Flat Management screen or have a separate confirmation process.


            if pk:
                 messages.success(request, f"'{blok.ad}' bloğu başarıyla güncellendi.")
                 return redirect('yonetim:blok_yonetimi') # Güncelleme sonrası listeye dön
            else:
                 messages.success(request, f"'{blok.ad}' bloğu başarıyla eklendi.")
                 return redirect('yonetim:blok_yonetimi') # Ekleme sonrası listeye dön

        else:
            # Form geçerli değilse, hataları göstererek aynı sayfayı render et
            # If the form is not valid, render the same page showing errors
            messages.error(request, "Lütfen formdaki hataları düzeltin.")
            bloklar = Blok.objects.filter(site=site_obj).order_by('ad')
            
            # Düzenleme modunda ise tekrar instance'ı forma geçir
            # If in edit mode, pass the instance to the form again
            if pk:
                 try:
                      blok_instance = get_object_or_404(Blok, pk=pk, site=site_obj)
                      form_title = f"'{blok_instance.ad}' Bloğunu Düzenle"
                 except Http404:
                      form_title = "Yeni Blok Ekle" # Blok bulunamazsa ekleme moduna dön
                      pk = None # pk'yı None yap ki context'te düzgün geçsin
            else:
                 form_title = "Yeni Blok Ekle"

            context = {
                'site': site_obj,
                'bloklar': bloklar,
                'form': form_instance,
                'form_title': form_title,
                'site_genel_aidat': site_obj.aidat_miktari,
                'editing_blok_id': pk # Template'de düzenleme modunda olup olmadığımızı anlamak için
            }
            return render(request, self.template_name, context)
