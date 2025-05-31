from django import template
# from yonetim.utils import get_user_site as get_user_site_util # utils.py'den import ediliyor

register = template.Library()

@register.filter(name='get_user_site')
def get_user_site_tag(user):
    """
    Template filter to get the site associated with the user.
    Kullanıcı ile ilişkili siteyi getiren template filtresi.
    """
    from yonetim.utils import get_user_site as get_user_site_util # IMPORT'U BURAYA TAŞI
    if not user or not user.is_authenticated:
        return None
    return get_user_site_util(user) 