from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Kullanici, Site, Blok, Daire, Aidat, Gider

class KullaniciAdmin(UserAdmin):
    """
    Özel Kullanici modeli için admin sınıfı.
    Custom admin class for Kullanici model.
    """
    form = UserChangeForm
    add_form = UserCreationForm
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_yonetici')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_yonetici', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username',)}),
        (_('Kişisel Bilgiler'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('İzinler'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_yonetici', 'groups', 'user_permissions'),
        }),
        (_('Önemli Tarihler'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Şifre değişikliklerini yönet.
        Handle password changes.
        """
        if not change:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)

# Register your models here.

# Daire modelini admin paneline ekle - Add Daire model to admin
admin.site.register(Daire)
# Kullanici modelini admin paneline ekle - Add Kullanici model to admin
admin.site.register(Kullanici, KullaniciAdmin)
# Blok modelini admin paneline ekle - Add Blok model to admin
admin.site.register(Blok)
# Site modelini admin paneline ekle - Add Site model to admin
admin.site.register(Site)
# Aidat modelini admin paneline ekle - Add Aidat model to admin
admin.site.register(Aidat)
# Gider modelini admin paneline ekle - Add Gider model to admin
admin.site.register(Gider)
