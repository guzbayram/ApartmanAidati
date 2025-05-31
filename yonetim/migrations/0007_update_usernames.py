from django.db import migrations

def update_usernames(apps, schema_editor):
    """
    Mevcut kullanıcı adlarını yeni formata güncelle
    Update existing usernames to new format
    """
    Kullanici = apps.get_model('yonetim', 'Kullanici')
    for user in Kullanici.objects.all():
        if user.site_kodu and not user.username.endswith(f"_{user.site_kodu}"):
            old_username = user.username
            user.username = f"{user.username}_{user.site_kodu}"
            print(f"Kullanıcı adı güncellendi: {old_username} -> {user.username}")
            user.save()

def reverse_update_usernames(apps, schema_editor):
    """
    Kullanıcı adlarını eski haline getir
    Revert usernames to old format
    """
    Kullanici = apps.get_model('yonetim', 'Kullanici')
    for user in Kullanici.objects.all():
        if user.site_kodu and user.username.endswith(f"_{user.site_kodu}"):
            old_username = user.username
            user.username = user.username[:-len(user.site_kodu)-1]  # Remove "_site_kodu" from end
            print(f"Kullanıcı adı eski haline getirildi: {old_username} -> {user.username}")
            user.save()

class Migration(migrations.Migration):
    dependencies = [
        ('yonetim', '0006_alter_kullanici_username_constraint'),
    ]

    operations = [
        migrations.RunPython(update_usernames, reverse_update_usernames),
    ] 