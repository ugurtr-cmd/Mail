from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
import uuid
from django.utils import timezone

class BaseModel(models.Model):
    """Tüm modeller için temel model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Company(BaseModel):
    """Şirket/Organizasyon modeli"""
    name = models.CharField(max_length=200, verbose_name="Şirket Adı")
    domain = models.CharField(max_length=100, blank=True, verbose_name="Web Sitesi")
    plan_type = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Ücretsiz'),
            ('starter', 'Starter'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise')
        ],
        default='free',
        verbose_name="Plan Türü"
    )
    max_subscribers = models.IntegerField(default=1000, verbose_name="Maksimum Abone")
    max_emails_per_month = models.IntegerField(default=10000, verbose_name="Aylık Maksimum E-posta")
    
    def __str__(self):
        return self.name

class UserProfile(BaseModel):
    """Kullanıcı profil modeli"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    timezone = models.CharField(max_length=50, default='Europe/Istanbul', verbose_name="Zaman Dilimi")
    email_signature = models.TextField(blank=True, verbose_name="E-posta İmzası")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Profil Resmi")
    
    def __str__(self):
        return f"{self.user.username} Profili"

class MailList(BaseModel):
    """E-posta liste modeli"""
    LIST_TYPES = (
        ('customer', 'Müşteri'),
        ('lead', 'Lead'),
        ('test', 'Test'),
        ('vip', 'VIP'),
        ('general', 'Genel'),
        ('newsletter', 'Bülten'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mail_lists')
    name = models.CharField(max_length=200, verbose_name="Liste Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    list_type = models.CharField(
        max_length=20, 
        choices=LIST_TYPES, 
        default='general',
        verbose_name="Liste Türü"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    subscriber_count = models.IntegerField(default=0, verbose_name="Abone Sayısı")
    unsubscribed_count = models.IntegerField(default=0, verbose_name="Abonelikten Çıkanlar")
    
    class Meta:
        verbose_name = "Mail Listesi"
        verbose_name_plural = "Mail Listeleri"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.subscriber_count})"
    
    def update_counts(self):
        """Abone sayılarını günceller"""
        self.subscriber_count = self.subscribers.filter(is_active=True).count()
        self.unsubscribed_count = self.subscribers.filter(is_active=False).count()
        self.save()

    def save(self, *args, **kwargs):
        # Abone sayısını otomatik güncelle
        if self.pk:
            self.subscriber_count = self.subscribers.filter(is_active=True).count()
            self.unsubscribed_count = self.subscribers.filter(is_active=False).count()
        super().save(*args, **kwargs)

    def update_counts(self):
        """Abone sayılarını manuel güncelle"""
        self.subscriber_count = self.subscribers.filter(is_active=True).count()
        self.unsubscribed_count = self.subscribers.filter(is_active=False).count()
        self.save()

class Subscriber(BaseModel):
    """Abone modeli"""
    mail_list = models.ForeignKey(
        MailList, 
        on_delete=models.CASCADE, 
        related_name='subscribers'
    )
    email = models.EmailField(
        verbose_name="E-posta",
        validators=[EmailValidator()]
    )
    name = models.CharField(max_length=100, blank=True, verbose_name="Ad Soyad")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    company = models.CharField(max_length=100, blank=True, verbose_name="Şirket")
    
    # Abonelik durumu
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    is_verified = models.BooleanField(default=False, verbose_name="Doğrulanmış")
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name="Abonelik Tarihi")
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name="Abonelikten Çıkış Tarihi")
    
    # Meta veriler
    source = models.CharField(max_length=100, blank=True, verbose_name="Kaynak")
    tags = models.JSONField(default=list, blank=True, verbose_name="Etiketler")
    custom_fields = models.JSONField(default=dict, blank=True, verbose_name="Özel Alanlar")
    
    class Meta:
        verbose_name = "Abone"
        verbose_name_plural = "Aboneler"
        unique_together = ['mail_list', 'email']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.mail_list.name}"
    
    def unsubscribe(self):
        """Aboneliği sonlandırır"""
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save()
        self.mail_list.update_counts()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mail listesi sayılarını güncelle
        if self.mail_list_id:
            self.mail_list.update_counts()
    
    def delete(self, *args, **kwargs):
        mail_list = self.mail_list
        super().delete(*args, **kwargs)
        # Mail listesi sayılarını güncelle
        if mail_list:
            mail_list.update_counts()

class EmailTemplate(BaseModel):
    """E-posta şablon modeli"""
    TEMPLATE_TYPES = (
        ('basic', 'Basit'),
        ('newsletter', 'Bülten'),
        ('promotional', 'Promosyon'),
        ('transactional', 'Transactional'),
        ('custom', 'Özel'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=200, verbose_name="Şablon Adı")
    template_type = models.CharField(
        max_length=20, 
        choices=TEMPLATE_TYPES, 
        default='basic',
        verbose_name="Şablon Türü"
    )
    subject = models.CharField(max_length=200, verbose_name="Konu")
    content = models.TextField(verbose_name="İçerik")
    html_content = models.TextField(blank=True, verbose_name="HTML İçerik")
    is_default = models.BooleanField(default=False, verbose_name="Varsayılan Şablon")
    
    class Meta:
        verbose_name = "E-posta Şablonu"
        verbose_name_plural = "E-posta Şablonları"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class Campaign(BaseModel):
    """Kampanya modeli"""
    STATUS_CHOICES = (
        ('draft', 'Taslak'),
        ('scheduled', 'Planlandı'),
        ('sending', 'Gönderiliyor'),
        ('sent', 'Gönderildi'),
        ('paused', 'Durduruldu'),
        ('failed', 'Başarısız'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=200, verbose_name="Kampanya Adı")
    subject = models.CharField(max_length=200, verbose_name="Konu")
    preheader = models.CharField(max_length=100, blank=True, verbose_name="Ön Başlık")
    
    # İçerik
    content = models.TextField(verbose_name="İçerik")
    html_content = models.TextField(blank=True, verbose_name="HTML İçerik")
    template = models.ForeignKey(
        EmailTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Şablon"
    )
    
    # Hedefleme
    mail_lists = models.ManyToManyField(MailList, verbose_name="Hedef Listeler")
    segments = models.JSONField(default=list, blank=True, verbose_name="Segmentler")
    
    # Zamanlama
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name="Durum"
    )
    scheduled_time = models.DateTimeField(null=True, blank=True, verbose_name="Planlanan Zaman")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gönderim Zamanı")
    
    # A/B Test
    is_ab_test = models.BooleanField(default=False, verbose_name="A/B Test")
    ab_test_subject = models.CharField(max_length=200, blank=True, verbose_name="A/B Test Konusu")
    ab_test_percentage = models.IntegerField(default=50, verbose_name="A/B Test Yüzdesi")
    
    # İstatistikler
    total_sent = models.IntegerField(default=0, verbose_name="Toplam Gönderim")
    delivered = models.IntegerField(default=0, verbose_name="Teslim Edilen")
    opens = models.IntegerField(default=0, verbose_name="Açılma")
    unique_opens = models.IntegerField(default=0, verbose_name="Benzersiz Açılma")
    clicks = models.IntegerField(default=0, verbose_name="Tıklanma")
    unique_clicks = models.IntegerField(default=0, verbose_name="Benzersiz Tıklanma")
    bounces = models.IntegerField(default=0, verbose_name="Geri Dönenler")
    complaints = models.IntegerField(default=0, verbose_name="Şikayetler")
    unsubscribes = models.IntegerField(default=0, verbose_name="Abonelikten Çıkanlar")
    
    class Meta:
        verbose_name = "Kampanya"
        verbose_name_plural = "Kampanyalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_time']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def get_open_rate(self):
        """Açılma oranını hesaplar"""
        if self.total_sent > 0:
            return (self.unique_opens / self.total_sent) * 100
        return 0
    
    def get_click_rate(self):
        """Tıklanma oranını hesaplar"""
        if self.total_sent > 0:
            return (self.unique_clicks / self.total_sent) * 100
        return 0
    
    def get_bounce_rate(self):
        """Geri dönüş oranını hesaplar"""
        if self.total_sent > 0:
            return (self.bounces / self.total_sent) * 100
        return 0
    
    def update_stats(self):
        """İstatistikleri gerçek zamanlı güncelle"""
        self.unique_opens = self.logs.filter(status='opened').values('subscriber').distinct().count()
        self.unique_clicks = self.logs.filter(status='clicked').values('subscriber').distinct().count()
        self.save()

class Automation(BaseModel):
    """Otomasyon modeli"""
    TRIGGER_TYPES = (
        ('subscription', 'Abonelik'),
        ('date', 'Tarih'),
        ('behavior', 'Davranış'),
        ('webhook', 'Webhook'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='automations')
    name = models.CharField(max_length=200, verbose_name="Otomasyon Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    
    # Tetikleyici
    trigger_type = models.CharField(
        max_length=20, 
        choices=TRIGGER_TYPES, 
        default='subscription',
        verbose_name="Tetikleyici Türü"
    )
    trigger_config = models.JSONField(default=dict, verbose_name="Tetikleyici Ayarları")
    
    # Hedef
    mail_list = models.ForeignKey(
        MailList, 
        on_delete=models.CASCADE, 
        verbose_name="Hedef Liste"
    )
    
    # Zamanlama
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    delay_minutes = models.IntegerField(default=0, verbose_name="Gecikme (Dakika)")
    interval_minutes = models.IntegerField(default=60, verbose_name="Aralık (Dakika)")
    
    # İstatistikler
    total_triggered = models.IntegerField(default=0, verbose_name="Toplam Tetiklenme")
    total_sent = models.IntegerField(default=0, verbose_name="Toplam Gönderim")
    
    class Meta:
        verbose_name = "Otomasyon"
        verbose_name_plural = "Otomasyonlar"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_trigger_type_display()})"

class AutomationStep(BaseModel):
    """Otomasyon adım modeli"""
    automation = models.ForeignKey(
        Automation, 
        on_delete=models.CASCADE, 
        related_name='steps'
    )
    step_order = models.IntegerField(default=0, verbose_name="Adım Sırası")
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        verbose_name="Kampanya"
    )
    delay_days = models.IntegerField(default=0, verbose_name="Gecikme (Gün)")
    conditions = models.JSONField(default=dict, blank=True, verbose_name="Koşullar")
    
    class Meta:
        verbose_name = "Otomasyon Adımı"
        verbose_name_plural = "Otomasyon Adımları"
        ordering = ['step_order']
    
    def __str__(self):
        return f"{self.automation.name} - Adım {self.step_order}"

class EmailLog(BaseModel):
    """E-posta log modeli"""
    STATUS_CHOICES = (
        ('sent', 'Gönderildi'),
        ('delivered', 'Teslim Edildi'),
        ('opened', 'Açıldı'),
        ('clicked', 'Tıklandı'),
        ('bounced', 'Geri Döndü'),
        ('complained', 'Şikayet Edildi'),
        ('unsubscribed', 'Abonelikten Çıktı'),
    )
    
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    subscriber = models.ForeignKey(
        Subscriber, 
        on_delete=models.CASCADE, 
        related_name='email_logs'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        verbose_name="Durum"
    )
    message_id = models.CharField(max_length=200, blank=True, verbose_name="Mesaj ID")
    opened_at = models.DateTimeField(null=True, blank=True, verbose_name="Açılma Zamanı")
    clicked_at = models.DateTimeField(null=True, blank=True, verbose_name="Tıklanma Zamanı")
    bounce_type = models.CharField(max_length=50, blank=True, verbose_name="Geri Dönüş Türü")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Adresi")
    
    class Meta:
        verbose_name = "E-posta Logu"
        verbose_name_plural = "E-posta Logları"
        indexes = [
            models.Index(fields=['campaign', 'subscriber']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.subscriber.email} - {self.get_status_display()}"

class ClickTrack(BaseModel):
    """Tıklanma takip modeli"""
    email_log = models.ForeignKey(
        EmailLog, 
        on_delete=models.CASCADE, 
        related_name='clicks'
    )
    url = models.URLField(verbose_name="URL")
    click_count = models.IntegerField(default=1, verbose_name="Tıklanma Sayısı")
    
    class Meta:
        verbose_name = "Tıklanma Takibi"
        verbose_name_plural = "Tıklanma Takipleri"
        unique_together = ['email_log', 'url']
    
    def __str__(self):
        return f"{self.email_log.subscriber.email} - {self.url}"

class Blacklist(BaseModel):
    """Kara liste modeli"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklist')
    email = models.EmailField(verbose_name="E-posta", unique=True)
    reason = models.CharField(
        max_length=50,
        choices=[
            ('bounce', 'Geri Dönüş'),
            ('complaint', 'Şikayet'),
            ('manual', 'Manuel'),
            ('spam', 'Spam')
        ],
        default='bounce',
        verbose_name="Sebep"
    )
    description = models.TextField(blank=True, verbose_name="Açıklama")
    
    class Meta:
        verbose_name = "Kara Liste"
        verbose_name_plural = "Kara Liste"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {self.get_reason_display()}"

class Webhook(BaseModel):
    """Webhook modeli"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webhooks')
    name = models.CharField(max_length=200, verbose_name="Webhook Adı")
    url = models.URLField(verbose_name="Webhook URL")
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('subscription', 'Abonelik'),
            ('unsubscription', 'Abonelikten Çıkma'),
            ('campaign_sent', 'Kampanya Gönderildi'),
            ('email_opened', 'E-posta Açıldı'),
            ('email_clicked', 'E-posta Tıklandı'),
        ],
        verbose_name="Olay Türü"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    secret_key = models.CharField(max_length=100, blank=True, verbose_name="Gizli Anahtar")
    
    class Meta:
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
    
    def __str__(self):
        return f"{self.name} - {self.get_event_type_display()}"

class Analytics(BaseModel):
    """Analitik modeli"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(verbose_name="Tarih")
    
    # Genel istatistikler
    total_campaigns = models.IntegerField(default=0, verbose_name="Toplam Kampanya")
    total_subscribers = models.IntegerField(default=0, verbose_name="Toplam Abone")
    new_subscribers = models.IntegerField(default=0, verbose_name="Yeni Aboneler")
    unsubscribed = models.IntegerField(default=0, verbose_name="Abonelikten Çıkanlar")
    
    # E-posta istatistikleri
    emails_sent = models.IntegerField(default=0, verbose_name="Gönderilen E-postalar")
    emails_delivered = models.IntegerField(default=0, verbose_name="Teslim Edilenler")
    emails_opened = models.IntegerField(default=0, verbose_name="Açılanlar")
    emails_clicked = models.IntegerField(default=0, verbose_name="Tıklananlar")
    emails_bounced = models.IntegerField(default=0, verbose_name="Geri Dönenler")
    
    # Oranlar
    delivery_rate = models.FloatField(default=0, verbose_name="Teslim Oranı")
    open_rate = models.FloatField(default=0, verbose_name="Açılma Oranı")
    click_rate = models.FloatField(default=0, verbose_name="Tıklanma Oranı")
    bounce_rate = models.FloatField(default=0, verbose_name="Geri Dönüş Oranı")
    
    class Meta:
        verbose_name = "Analitik"
        verbose_name_plural = "Analitik"
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"
    
    def calculate_rates(self):
        """Oranları hesaplar"""
        if self.emails_sent > 0:
            self.delivery_rate = (self.emails_delivered / self.emails_sent) * 100
            self.open_rate = (self.emails_opened / self.emails_sent) * 100
            self.click_rate = (self.emails_clicked / self.emails_sent) * 100
            self.bounce_rate = (self.emails_bounced / self.emails_sent) * 100