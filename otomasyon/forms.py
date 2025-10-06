from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from .models import *

class CustomUserCreationForm(UserCreationForm):
    """Özelleştirilmiş kullanıcı kayıt formu"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'E-posta adresiniz'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Adınız'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Soyadınız'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kullanıcı adı'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Bu e-posta adresi zaten kullanılıyor.')
        return email

class UserProfileForm(forms.ModelForm):
    """Kullanıcı profil formu"""
    class Meta:
        model = UserProfile
        fields = ['phone', 'timezone', 'email_signature', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+90 555 123 45 67'
            }),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'email_signature': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'E-posta imzanız...'
            }),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class MailListForm(forms.ModelForm):
    """Mail listesi formu"""
    class Meta:
        model = MailList
        fields = ['name', 'description', 'list_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Liste adı'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Liste açıklaması...'
            }),
            'list_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['list_type'].empty_label = "Liste türü seçin"

class SubscriberForm(forms.ModelForm):
    """Abone formu"""
    class Meta:
        model = Subscriber
        fields = ['mail_list', 'email', 'name', 'phone', 'company', 'source', 'tags']
        widgets = {
            'mail_list': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ornek@email.com'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ad Soyad'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Telefon numarası'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Şirket adı'
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kaynak (web sitesi, form, vs.)'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'etiket1, etiket2, etiket3'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['mail_list'].queryset = MailList.objects.filter(user=self.user)
        
        self.fields['mail_list'].empty_label = "Mail listesi seçin"

    def clean_email(self):
        email = self.cleaned_data.get('email')
        mail_list = self.cleaned_data.get('mail_list')
        
        if mail_list and email:
            # Aynı mail listesinde aynı e-posta kontrolü
            existing = Subscriber.objects.filter(
                mail_list=mail_list, 
                email=email
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Bu e-posta adresi zaten bu listede mevcut.')
        
        return email

    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        if tags:
            # Virgülle ayrılmış etiketleri listeye çevir
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            return tag_list
        return []

class EmailTemplateForm(forms.ModelForm):
    """E-posta şablon formu"""
    class Meta:
        model = EmailTemplate
        fields = ['name', 'template_type', 'subject', 'content', 'html_content', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Şablon adı'
            }),
            'template_type': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E-posta konusu'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'E-posta içeriği...'
            }),
            'html_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': 'HTML içerik (isteğe bağlı)...'
            }),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

class CampaignForm(forms.ModelForm):
    """Kampanya formu"""
    send_now = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Hemen gönder'
    )
    
    schedule_later = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Sonra gönder'
    )

    class Meta:
        model = Campaign
        fields = [
            'name', 'subject', 'preheader', 'content', 'html_content', 
            'template', 'mail_lists', 'scheduled_time', 'is_ab_test',
            'ab_test_subject', 'ab_test_percentage'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kampanya adı'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E-posta konusu',
                'id': 'campaign-subject'
            }),
            'preheader': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ön başlık (isteğe bağlı)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'E-posta içeriği...',
                'id': 'campaign-content'
            }),
            'html_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'HTML içerik (isteğe bağlı)...'
            }),
            'template': forms.Select(attrs={'class': 'form-control'}),
            'mail_lists': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 6
            }),
            'scheduled_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_ab_test': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ab_test_subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'A/B test konusu'
            }),
            'ab_test_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 10,
                'max': 90,
                'step': 5
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['mail_lists'].queryset = MailList.objects.filter(user=self.user)
            self.fields['template'].queryset = EmailTemplate.objects.filter(user=self.user)
        
        # Zaman formatı ayarı
        if self.instance and self.instance.scheduled_time:
            self.fields['scheduled_time'].initial = self.instance.scheduled_time.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        send_now = cleaned_data.get('send_now')
        schedule_later = cleaned_data.get('schedule_later')
        scheduled_time = cleaned_data.get('scheduled_time')
        
        if send_now and schedule_later:
            raise ValidationError('Hem "hemen gönder" hem de "sonra gönder" seçemezsiniz.')
        
        if schedule_later and not scheduled_time:
            raise ValidationError('Planlı gönderim için tarih seçmelisiniz.')
        
        if scheduled_time and scheduled_time < timezone.now():
            raise ValidationError('Geçmiş bir tarih seçemezsiniz.')
        
        return cleaned_data

    def clean_ab_test_percentage(self):
        percentage = self.cleaned_data.get('ab_test_percentage')
        if percentage and (percentage < 10 or percentage > 90):
            raise ValidationError('A/B test yüzdesi 10-90 arasında olmalıdır.')
        return percentage

class AutomationForm(forms.ModelForm):
    """Otomasyon formu"""
    class Meta:
        model = Automation
        fields = ['name', 'description', 'trigger_type', 'trigger_config', 'mail_list', 'delay_minutes', 'interval_minutes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Otomasyon adı'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Otomasyon açıklaması...'
            }),
            'trigger_type': forms.Select(attrs={'class': 'form-control'}),
            'trigger_config': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tetikleyici ayarları (JSON formatında)...'
            }),
            'mail_list': forms.Select(attrs={'class': 'form-control'}),
            'delay_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1,
                'placeholder': '0'
            }),
            'interval_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'step': 1,
                'placeholder': '60'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['mail_list'].queryset = MailList.objects.filter(user=self.user)

    def clean_trigger_config(self):
        trigger_config = self.cleaned_data.get('trigger_config')
        if trigger_config:
            try:
                # JSON validasyonu
                import json
                json.loads(trigger_config)
            except json.JSONDecodeError:
                raise ValidationError('Geçersiz JSON formatı.')
        return trigger_config

    def clean_delay_minutes(self):
        delay = self.cleaned_data.get('delay_minutes')
        if delay and delay < 0:
            raise ValidationError('Gecikme süresi negatif olamaz.')
        return delay

    def clean_interval_minutes(self):
        interval = self.cleaned_data.get('interval_minutes')
        if interval and interval < 1:
            raise ValidationError('Aralık en az 1 dakika olmalıdır.')
        return interval

class AutomationStepForm(forms.ModelForm):
    """Otomasyon adım formu"""
    class Meta:
        model = AutomationStep
        fields = ['step_order', 'campaign', 'delay_days', 'conditions']
        widgets = {
            'step_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'step': 1
            }),
            'campaign': forms.Select(attrs={'class': 'form-control'}),
            'delay_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1,
                'placeholder': '0'
            }),
            'conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Koşullar (JSON formatında)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.automation = kwargs.pop('automation', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['campaign'].queryset = Campaign.objects.filter(user=self.user)

    def clean_step_order(self):
        step_order = self.cleaned_data.get('step_order')
        if self.automation and step_order:
            # Aynı sırada başka adım var mı kontrol et
            existing = AutomationStep.objects.filter(
                automation=self.automation,
                step_order=step_order
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Bu sırada zaten bir adım mevcut.')
        
        return step_order

class BlacklistForm(forms.ModelForm):
    """Kara liste formu"""
    class Meta:
        model = Blacklist
        fields = ['email', 'reason', 'description']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ornek@email.com'
            }),
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Açıklama (isteğe bağlı)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user and email:
            # Aynı kullanıcı için aynı e-posta kontrolü
            existing = Blacklist.objects.filter(user=self.user, email=email)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Bu e-posta adresi zaten kara listede mevcut.')
        
        return email

class WebhookForm(forms.ModelForm):
    """Webhook formu"""
    class Meta:
        model = Webhook
        fields = ['name', 'url', 'event_type', 'secret_key']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Webhook adı'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://ornek.com/webhook'
            }),
            'event_type': forms.Select(attrs={'class': 'form-control'}),
            'secret_key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Gizli anahtar (isteğe bağlı)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_url(self):
        url = self.cleaned_data.get('url')
        if url and not url.startswith(('http://', 'https://')):
            raise ValidationError('URL http:// veya https:// ile başlamalıdır.')
        return url

class CSVImportForm(forms.Form):
    """CSV içe aktarma formu"""
    csv_file = forms.FileField(
        label='CSV Dosyası',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.txt'
        })
    )
    has_headers = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Dosyada başlık satırı var'
    )
    
    email_column = forms.CharField(
        initial='email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'email'
        }),
        help_text='E-posta sütununun adı'
    )
    
    name_column = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'name'
        }),
        help_text='İsim sütununun adı (isteğe bağlı)'
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # Dosya uzantısı kontrolü
            if not csv_file.name.endswith('.csv'):
                raise ValidationError('Lütfen geçerli bir CSV dosyası yükleyin.')
            
            # Dosya boyutu kontrolü (max 5MB)
            if csv_file.size > 5 * 1024 * 1024:
                raise ValidationError('Dosya boyutu 5MB\'dan küçük olmalıdır.')
        
        return csv_file

class CampaignScheduleForm(forms.Form):
    """Kampanya planlama formu"""
    scheduled_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Planlanan Zaman'
    )
    
    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time and scheduled_time < timezone.now():
            raise ValidationError('Geçmiş bir tarih seçemezsiniz.')
        return scheduled_time

class EmailSettingsForm(forms.Form):
    """E-posta ayarları formu"""
    smtp_host = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'smtp.gmail.com'
        }),
        label='SMTP Sunucusu'
    )
    smtp_port = forms.IntegerField(
        initial=587,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 65535
        }),
        label='SMTP Port'
    )
    smtp_username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'kullanici@gmail.com'
        }),
        label='SMTP Kullanıcı Adı'
    )
    smtp_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifre'
        }),
        label='SMTP Şifre',
        required=False
    )
    use_tls = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='TLS Kullan'
    )
    default_from_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'gonderim@firma.com'
        }),
        label='Varsayılan Gönderen'
    )

class APISettingsForm(forms.Form):
    """API ayarları formu"""
    api_key = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        label='API Anahtarı'
    )
    api_secret = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        label='API Gizli Anahtar'
    )
    webhook_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://firma.com/webhook'
        }),
        label='Webhook URL'
    )

class BulkActionForm(forms.Form):
    """Toplu işlem formu"""
    ACTION_CHOICES = [
        ('delete', 'Sil'),
        ('activate', 'Aktif Et'),
        ('deactivate', 'Pasif Et'),
        ('export', 'Dışa Aktar'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='İşlem'
    )
    items = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    def clean_items(self):
        items = self.cleaned_data.get('items')
        if items:
            try:
                # JSON array validasyonu
                import json
                item_list = json.loads(items)
                if not isinstance(item_list, list):
                    raise ValidationError('Geçersiz veri formatı.')
                return item_list
            except json.JSONDecodeError:
                raise ValidationError('Geçersiz JSON formatı.')
        return []

class SearchForm(forms.Form):
    """Arama formu"""
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ara...'
        }),
        label=''
    )
    
    search_field = forms.ChoiceField(
        choices=[
            ('email', 'E-posta'),
            ('name', 'İsim'),
            ('company', 'Şirket'),
        ],
        initial='email',
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label='Arama Alanı'
    )

class FilterForm(forms.Form):
    """Filtre formu"""
    list_type = forms.ChoiceField(
        choices=[('', 'Tümü')] + list(MailList.LIST_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Liste Türü'
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Tümü')] + list(Campaign.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Durum'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Başlangıç Tarihi'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Bitiş Tarihi'
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('Başlangıç tarihi bitiş tarihinden büyük olamaz.')
        
        return cleaned_data