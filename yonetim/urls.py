from django.urls import path
from . import views

app_name = 'yonetim'  # Define app_name for namespacing

urlpatterns = [
    path('', views.panel_view, name='anasayfa'),  # Boş path için panel_view'e yönlendirme
    # Kullanıcı İşlemleri / User Operations
    path('giris/', views.giris_view, name='giris'),
    path('kayit/', views.kayit_view, name='kayit'),
    path('cikis/', views.cikis_view, name='cikis'),
    
    # Ana Panel / Main Panel
    path('panel/', views.panel_view, name='panel'),
    
    # Site Bilgileri / Site Information
    path('site-bilgi/', views.site_bilgi_view, name='site_bilgi'),
    
    # AJAX View'ları / AJAX Views
    path('ajax/blok-getir/', views.ajax_blok_getir, name='ajax_blok_getir'),
    path('ajax/daire-borc-sorgula/', views.ajax_daire_borc_sorgula, name='ajax_daire_borc_sorgula'),

    # CRUD Yönetim Linkleri (İskelet)
    path('blok-yonetimi/', views.BlokYonetimView.as_view(), name='blok_yonetimi'),
    # Blok Düzenleme URL'si
    # Block Edit URL
    path('blok-yonetimi/duzenle/<int:pk>/', views.BlokYonetimView.as_view(), name='blok_duzenle'),
    # Daire Yönetimi URL'leri
    # Flat Management URLs
    path('daire-yonetimi/', views.daire_yonetimi_view, name='daire_yonetimi'),
    path('daire-yonetimi/blok/<int:blok_id>/', views.daire_yonetimi_view, name='daire_yonetimi_blok'), # Blok ID'si ile filtreleme için

    # path('daire/ekle/', views.daire_ekle_view, name='daire_ekle'),
    # path('daire/duzenle/<int:daire_id>/', views.daire_duzenle_view, name='daire_duzenle'),

    # Aidat Yönetimi URL'leri / Due Management URLs
    path('aidatlar/', views.aidat_yonetimi_view, name='aidat_yonetimi'), # Genel aidat listesi (yönetici)
    path('aidatlar/daire/<int:daire_id>/', views.aidat_yonetimi_view, name='aidat_yonetimi'), # Daireye özel aidatlar (aynı view, farklı URL)
    path('giderler/', views.gider_yonetimi_view, name='gider_yonetimi'),
    path('kullanicilar/', views.kullanici_yonetimi_view, name='kullanici_yonetimi'),

    # Raporlama Linkleri (İskelet)
    path('rapor/yillik/', views.yillik_rapor_pdf_view, name='yillik_rapor_pdf_default'),
    path('rapor/yillik/<int:yil>/pdf/', views.yillik_rapor_pdf_view, name='yillik_rapor_pdf'),
    path('rapor/aylik/', views.aylik_rapor_view, name='aylik_rapor_default'),
    path('rapor/aylik/<int:yil>/<int:ay>/', views.aylik_rapor_view, name='aylik_rapor'),

    # Veri Import/Export (İskelet)
    path('veri/import-export/', views.import_export_view, name='import_export'),

    # Aşağıdaki path'ler henüz views.py'de tanımlı olmadığı için yorum satırı yapıldı.
    # These paths are commented out as they are not yet defined in views.py.
    # path('aidat/<int:aidat_id>/guncelle/', views.aidat_update_view, name='aidat_update'),
    # path('aidat/<int:aidat_id>/sil/', views.aidat_delete_view, name='aidat_delete'),
    # path('gider/<int:gider_id>/guncelle/', views.gider_update_view, name='gider_update'),
    # path('gider/<int:gider_id>/sil/', views.gider_delete_view, name='gider_delete'),
    # path('daire/<int:daire_id>/odeme-detay/', views.daire_odeme_detay_view, name='daire_odeme_detay'),
    # path('rapor/yillik-pdf-olustur/', views.olustur_yillik_pdf_raporu_view, name='olustur_yillik_pdf_raporu'),
    # path('rapor/yillik-rapor/<int:rapor_id>/sil/', views.delete_yillik_rapor_view, name='delete_yillik_rapor'),
    # path('veri/indir/', views.download_all_data_view, name='download_all_data'),
    # path('veri/yukle-csv/', views.upload_data_csv_view, name='upload_data_csv'),
    # path('ajax/get-aidat-form/<int:daire_id>/', views.get_aidat_form_html_view, name='get_aidat_form_html'),
    # path('ajax/get-aidat-form/duzenle/<int:aidat_id>/', views.get_aidat_form_html_view, name='get_aidat_form_html_edit'), # For editing
    # path('ajax/get-gider-form/', views.get_gider_form_html_view, name='get_gider_form_html'),
    # path('ajax/get-gider-form/duzenle/<int:gider_id>/', views.get_gider_form_html_view, name='get_gider_form_html_edit'), # For editing
    # path('ajax/update-item-in-modal/<str:model_name>/<int:item_id>/', views.update_item_in_modal_view, name='update_item_in_modal'),
    # path('ajax/create-item-in-modal/<str:model_name>/<int:parent_id>/', views.create_item_in_modal_view, name='create_item_in_modal'), 
] 