from django.conf import settings

def global_settings(request):
    """Global template context variables"""
    return {
        'SITE_NAME': 'EmailOtomasyon',
        'SITE_URL': 'http://localhost:8000',
        'SUPPORT_EMAIL': 'destek@emailotomasyon.com',
        'COMPANY_NAME': 'EmailOtomasyon Ltd.',
    }

def user_notifications(request):
    """Kullanıcı bildirimleri"""
    if request.user.is_authenticated:
        # Örnek: Bekleyen kampanyalar sayısı
        pending_campaigns = 0
        # Burada gerçek verileri ekleyebilirsiniz
        return {
            'pending_campaigns': pending_campaigns,
        }
    return {}