from django.apps import apps # Site modeline erişim için

def get_user_site(user):
    """ Kullanıcının ilişkili olduğu ilk siteyi döndürür (yönetici veya sakin olarak). """
    if not user.is_authenticated:
        return None
    
    Site = apps.get_model('yonetim', 'Site')

    if user.is_yonetici:
        site = Site.objects.filter(yonetici=user).first()
        if site:
            return site
    
    if hasattr(user, 'sakin_oldugu_daire') and user.sakin_oldugu_daire:
        return user.sakin_oldugu_daire.blok.site
    elif user.aktif_daire:
        return user.aktif_daire.blok.site
    
    if user.site_kodu:
        try:
            return Site.objects.get(kod=user.site_kodu)
        except Site.DoesNotExist:
            return None
    return None

def get_user_daire(user):
    """ Kullanıcının aktif dairesini veya sakin olduğu daireyi döndürür. """
    if not user.is_authenticated:
        return None
    if hasattr(user, 'sakin_oldugu_daire') and user.sakin_oldugu_daire:
        return user.sakin_oldugu_daire
    if user.aktif_daire:
        return user.aktif_daire
    return None

def daire_natural_sort_key(daire):
    """ Daireleri doğal sıralama için anahtar fonksiyonu. (Bu zaten modelde get_sortable_daire_no olarak var, belki utils'e gerek yok) """
    # Bu fonksiyon Daire modelindeki get_sortable_daire_no metodunu kullanıyor.
    # Eğer Daire instance'ı üzerinden çağrılacaksa utils'de olmasına gerek yok.
    # Eğer Daire listesi sıralanırken key olarak kullanılacaksa ve Daire modelini import etmek istemiyorsak burada kalabilir.
    # Şimdilik views.py'daki kullanıma benzer şekilde bırakıyorum.
    return daire.get_sortable_daire_no() # Daire modelinin import edilmesi veya apps.get_model ile alınması gerekir.

# Not: daire_natural_sort_key, Daire modeline erişim gerektirir.
# Eğer bu utils.py dosyası modellerden de önce yükleniyorsa, bu da sorun yaratabilir.
# En güvenlisi Daire modelini import etmek veya apps.get_model kullanmak.
# Şimdilik Daire modelinin bu fonksiyon çağrıldığında zaten tanımlı/erişilebilir olduğunu varsayıyoruz. 