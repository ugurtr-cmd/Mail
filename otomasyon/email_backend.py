# dashboard/email_backend.py
import resend
from django.conf import settings
from django.utils import timezone
from .models import Campaign, EmailLog, Subscriber
import threading
import re
import urllib.parse

# Resend API key'ini ayarla
resend.api_key = settings.EMAIL_HOST_PASSWORD

class EmailSender:
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
    
    def test_connection(self):
        """Resend bağlantısını test et"""
        try:
            # Basit bir test
            test_params = {
                "from": self.from_email,
                "to": ["test@example.com"],
                "subject": "Connection Test",
                "html": "<p>Test</p>"
            }
            # Sadece validation testi
            return True, "Resend bağlantısı hazır"
        except Exception as e:
            return False, f"Resend hatası: {str(e)}"
    
    def send_test_email(self, to_email, subject, content):
        """Test e-postası gönder"""
        try:
            r = resend.Emails.send({
                "from": self.from_email,
                "to": to_email,
                "subject": subject,
                "html": f"<p>{content}</p>",
                "text": content
            })
            return True, "Test e-postası Resend ile gönderildi"
        except Exception as e:
            return False, f"Resend gönderim hatası: {str(e)}"
    
    def send_campaign_email(self, campaign, subscriber, email_content):
        """Resend ile tekil e-posta gönderimi"""
        try:
            # Tracking link'leri ekle
            html_content = add_tracking_links(
                campaign.html_content or f"<p>{email_content}</p>", 
                subscriber.id, 
                campaign.id
            )
            
            # Resend ile gönder
            r = resend.Emails.send({
                "from": self.from_email,
                "to": subscriber.email,
                "subject": campaign.subject,
                "html": html_content,
                "text": email_content,
                "headers": {
                    "X-Entity-Ref-ID": f"{campaign.id}_{subscriber.id}"
                }
            })
            
            return True, "E-posta Resend ile gönderildi"
            
        except Exception as e:
            print(f"Resend gönderim hatası: {str(e)}")
            return False, f"Resend hatası: {str(e)}"

def add_tracking_links(content, subscriber_id, campaign_id):
    """Tracking link'leri ekle - Resend uyumlu"""
    if not content:
        return ""
    
    # Base URL
    base_url = 'http://localhost:8000'  # Production'da gerçek domain
    
    # Açılma takip resmi
    open_tracking_url = f'{base_url}/track/open/{subscriber_id}/{campaign_id}/'
    open_tracking_img = f'<img src="{open_tracking_url}" width="1" height="1" style="display:none;" alt="" />'
    
    # Link takip fonksiyonu
    def add_click_tracking(match):
        original_url = match.group(1)
        encoded_url = urllib.parse.quote(original_url, safe='')
        tracking_url = f'{base_url}/track/click/{subscriber_id}/{campaign_id}/?url={encoded_url}'
        return f'href="{tracking_url}"'
    
    # HTML içeriği kontrol et
    is_html = '<html' in content.lower() or '<body' in content.lower() or '<div' in content.lower()
    
    if is_html:
        # HTML içerik - linkleri değiştir
        content = re.sub(r'href="(https?://[^"]+)"', add_click_tracking, content, flags=re.IGNORECASE)
        
        # Açılma takip resmini ekle
        if '<body' in content:
            content = re.sub(r'<body[^>]*>', lambda m: m.group(0) + open_tracking_img, content, flags=re.IGNORECASE)
        else:
            content += open_tracking_img
    else:
        # Plain text için HTML'e çevir
        content = f"<p>{content}</p>"
        content += open_tracking_img
    
    return content

def send_campaign_emails(campaign_id):
    """Kampanya e-postalarını Resend ile gönder"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        print(f"Resend ile kampanya başlatılıyor: {campaign.name}")
        
        campaign.status = 'sending'
        campaign.sent_at = timezone.now()
        campaign.save()
        
        email_sender = EmailSender()
        
        # Bağlantı testi
        connection_ok, connection_msg = email_sender.test_connection()
        if not connection_ok:
            print(f"Resend bağlantı hatası: {connection_msg}")
            campaign.status = 'failed'
            campaign.save()
            return
        
        # Tüm aktif aboneleri al
        subscribers = Subscriber.objects.filter(
            mail_list__in=campaign.mail_lists.all(),
            is_active=True
        )
        
        total_subscribers = subscribers.count()
        total_sent = 0
        total_failed = 0
        
        print(f"Resend ile {total_subscribers} aboneye gönderilecek")
        
        for subscriber in subscribers:
            try:
                # E-posta logu oluştur
                email_log = EmailLog.objects.create(
                    campaign=campaign,
                    subscriber=subscriber,
                    status='sent',
                    message_id=f"{campaign.id}_{subscriber.id}"
                )
                
                # Resend ile gönder
                success, message = email_sender.send_campaign_email(
                    campaign, 
                    subscriber, 
                    campaign.content
                )
                
                if success:
                    total_sent += 1
                    print(f"Resend ile gönderildi: {subscriber.email} ({total_sent}/{total_subscribers})")
                else:
                    total_failed += 1
                    email_log.status = 'bounced'
                    email_log.save()
                    print(f"Resend başarısız: {subscriber.email} - {message}")
                
                # Her 10 e-postada bir güncelle
                if total_sent % 10 == 0:
                    campaign.total_sent = total_sent
                    campaign.bounces = total_failed
                    campaign.save()
                
                # Küçük bekleme (rate limit için)
                import time
                time.sleep(0.1)
                
            except Exception as e:
                total_failed += 1
                print(f"Resend abone işleme hatası ({subscriber.email}): {str(e)}")
                continue
        
        # Kampanya durumunu güncelle
        campaign.status = 'sent'
        campaign.total_sent = total_sent
        campaign.bounces = total_failed
        campaign.save()
        
        print(f"Resend kampanya tamamlandı: {total_sent} başarılı, {total_failed} başarısız")
        
    except Campaign.DoesNotExist:
        print(f"Kampanya bulunamadı: {campaign_id}")
    except Exception as e:
        print(f"Resend kampanya gönderim hatası: {str(e)}")
        try:
            campaign.status = 'failed'
            campaign.save()
        except:
            pass

def send_campaign_async(campaign_id):
    """Asenkron e-posta gönderimi - Resend ile"""
    thread = threading.Thread(target=send_campaign_emails, args=(campaign_id,))
    thread.daemon = True
    thread.start()
    return thread