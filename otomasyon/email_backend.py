# dashboard/email_backend.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.core.mail import send_mail
from .models import Campaign, EmailLog, Subscriber
import threading
from django.utils import timezone

class EmailSender:
    def __init__(self):
        self.smtp_host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'EMAIL_PORT', 587)
        self.smtp_username = getattr(settings, 'EMAIL_HOST_USER', '')
        self.smtp_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
    
    def test_connection(self):
        """SMTP bağlantısını test et"""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            return True, "Bağlantı başarılı"
        except Exception as e:
            return False, f"SMTP hatası: {str(e)}"
    
    def send_test_email(self, to_email, subject, content):
        """Test e-postası gönder"""
        try:
            send_mail(
                subject,
                content,
                self.smtp_username,
                [to_email],
                fail_silently=False,
            )
            return True, "Test e-postası gönderildi"
        except Exception as e:
            return False, f"Test gönderim hatası: {str(e)}"
    
    def send_campaign_email(self, campaign, subscriber, email_content):
        """Tekil e-posta gönderimi"""
        try:
            # E-posta içeriğini oluştur
            message = MIMEMultipart('alternative')
            message['Subject'] = campaign.subject
            message['From'] = self.smtp_username
            message['To'] = subscriber.email
            
            # Plain text içerik
            text_part = MIMEText(email_content, 'plain', 'utf-8')
            message.attach(text_part)
            
            # HTML içerik (varsa)
            if campaign.html_content:
                html_content = add_tracking_links(campaign.html_content, subscriber.id, campaign.id)
                html_part = MIMEText(html_content, 'html', 'utf-8')
                message.attach(html_part)
            
            # SMTP bağlantısı
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            return True, "E-posta gönderildi"
            
        except Exception as e:
            print(f"E-posta gönderim hatası: {str(e)}")
            return False, f"Gönderim hatası: {str(e)}"

# dashboard/email_backend.py - Tracking fonksiyonunu güncelle
def add_tracking_links(content, subscriber_id, campaign_id):
    """Tracking link'leri ekle - Geliştirilmiş versiyon"""
    import re
    import urllib.parse
    
    if not content:
        return ""
    
    # Base URL (production'da gerçek domain kullanın)
    base_url = 'http://localhost:8000'
    
    # Açılma takip resmi
    open_tracking_url = f'{base_url}/track/open/{subscriber_id}/{campaign_id}/'
    open_tracking_img = f'<img src="{open_tracking_url}" width="1" height="1" style="display:none;" alt="" />'
    
    # Link takip fonksiyonu
    def add_click_tracking(match):
        original_url = match.group(1)
        # URL'yi encode et
        encoded_url = urllib.parse.quote(original_url, safe='')
        tracking_url = f'{base_url}/track/click/{subscriber_id}/{campaign_id}/?url={encoded_url}'
        return f'href="{tracking_url}"'
    
    # HTML içeriği kontrol et
    is_html = '<html' in content.lower() or '<body' in content.lower() or '<div' in content.lower()
    
    if is_html:
        # HTML içerik - linkleri değiştir ve tracking resmi ekle
        content = re.sub(r'href="(https?://[^"]+)"', add_click_tracking, content, flags=re.IGNORECASE)
        
        # Açılma takip resmini ekle (body içine)
        if '<body' in content:
            content = re.sub(r'<body[^>]*>', lambda m: m.group(0) + open_tracking_img, content, flags=re.IGNORECASE)
        else:
            # Body tag yoksa, içeriğin sonuna ekle
            content += open_tracking_img
    else:
        # Plain text içerik - linkleri tracking link'ine çevir
        def add_click_tracking_text(match):
            original_url = match.group(1)
            encoded_url = urllib.parse.quote(original_url, safe='')
            tracking_url = f'{base_url}/track/click/{subscriber_id}/{campaign_id}/?url={encoded_url}'
            return tracking_url
        
        content = re.sub(r'(https?://[^\s]+)', add_click_tracking_text, content)
    
    return content

def send_campaign_emails(campaign_id):
    """Kampanya e-postalarını toplu gönder"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        print(f"Kampanya başlatılıyor: {campaign.name}")
        
        campaign.status = 'sending'
        campaign.sent_at = timezone.now()
        campaign.save()
        
        email_sender = EmailSender()
        
        # Önce SMTP bağlantısını test et
        connection_ok, connection_msg = email_sender.test_connection()
        if not connection_ok:
            print(f"SMTP bağlantı hatası: {connection_msg}")
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
        
        print(f"Toplam {total_subscribers} abone bulundu")
        
        for subscriber in subscribers:
            try:
                # E-posta logu oluştur
                email_log = EmailLog.objects.create(
                    campaign=campaign,
                    subscriber=subscriber,
                    status='sent',
                    message_id=f"{campaign.id}_{subscriber.id}"
                )
                
                # E-postayı gönder
                success, message = email_sender.send_campaign_email(
                    campaign, 
                    subscriber, 
                    campaign.content
                )
                
                if success:
                    total_sent += 1
                    print(f"Gönderildi: {subscriber.email} ({total_sent}/{total_subscribers})")
                else:
                    total_failed += 1
                    email_log.status = 'bounced'
                    email_log.save()
                    print(f"Başarısız: {subscriber.email} - {message}")
                
                # Her 10 e-postada bir kampanyayı güncelle
                if total_sent % 10 == 0:
                    campaign.total_sent = total_sent
                    campaign.bounces = total_failed
                    campaign.save()
                
                # Küçük bir bekleme (spam koruması için)
                import time
                time.sleep(0.1)
                
            except Exception as e:
                total_failed += 1
                print(f"Abone işleme hatası ({subscriber.email}): {str(e)}")
                continue
        
        # Kampanya durumunu güncelle
        campaign.status = 'sent'
        campaign.total_sent = total_sent
        campaign.bounces = total_failed
        campaign.save()
        
        print(f"Kampanya tamamlandı: {total_sent} başarılı, {total_failed} başarısız")
        
    except Campaign.DoesNotExist:
        print(f"Kampanya bulunamadı: {campaign_id}")
    except Exception as e:
        print(f"Kampanya gönderim hatası: {str(e)}")
        try:
            campaign.status = 'failed'
            campaign.save()
        except:
            pass

def send_campaign_async(campaign_id):
    """Asenkron e-posta gönderimi"""
    thread = threading.Thread(target=send_campaign_emails, args=(campaign_id,))
    thread.daemon = True
    thread.start()
    return thread