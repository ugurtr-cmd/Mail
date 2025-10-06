import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.core.paginator import Paginator
import csv
import json
from .models import *
from .forms import *

# Public Views
def index(request):
    """Ana sayfa"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

def public_subscribe(request):
    """Genel bülten aboneliği"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Genel abonelik listesine ekleme yapılabilir
            messages.success(request, 'Başarıyla abone oldunuz! Teşekkür ederiz.')
        else:
            messages.error(request, 'Lütfen geçerli bir e-posta adresi girin.')
        return redirect('index')
    return redirect('index')

# Authentication Views
def register(request):
    """Kullanıcı kayıt"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # UserProfile oluştur
            UserProfile.objects.create(user=user)
            
            # Kullanıcıyı otomatik login et
            login(request, user)
            messages.success(request, 'Hoş geldiniz! Hesabınız başarıyla oluşturuldu.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'auth/register.html', {'form': form})

# Dashboard Views
# views.py - Dashboard view'ını güncelle

# views.py - Dashboard view'ını güncelle
@login_required
def dashboard(request):
    """Dashboard ana sayfa - Tamamen dinamik veriler"""
    # Mail listeleri ve aboneler
    mail_lists = MailList.objects.filter(user=request.user)
    campaigns = Campaign.objects.filter(user=request.user)
    automations = Automation.objects.filter(user=request.user)
    
    # Dinamik hesaplamalar
    total_subscribers = Subscriber.objects.filter(
        mail_list__user=request.user, 
        is_active=True
    ).count()
    
    total_campaigns = campaigns.count()
    
    # Aktif otomasyon sayısı
    active_automations_count = automations.filter(is_active=True).count()
    
    # Son 30 günün istatistikleri
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_campaigns = campaigns.filter(sent_at__gte=thirty_days_ago)
    
    total_sent_recent = sum(c.total_sent for c in recent_campaigns)
    total_opens_recent = sum(c.opens for c in recent_campaigns)
    
    success_rate = 0
    if total_sent_recent > 0:
        success_rate = (total_opens_recent / total_sent_recent) * 100
    
    # Yaklaşan kampanyalar
    upcoming_campaigns = campaigns.filter(
        status='scheduled', 
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')[:5]
    
    # Son kampanyalar
    recent_campaigns_list = campaigns.order_by('-created_at')[:5]
    
    # Performans grafiği verileri
    performance_data = get_performance_data(request.user)
    
    context = {
        'mail_lists': mail_lists,
        'campaigns': recent_campaigns_list,
        'automations': automations,
        'total_subscribers': total_subscribers,
        'total_campaigns': total_campaigns,
        'success_rate': round(success_rate, 2),
        'upcoming_campaigns': upcoming_campaigns,
        'performance_data': performance_data,
        'total_sent_recent': total_sent_recent,
        'total_opens_recent': total_opens_recent,
        'active_automations_count': active_automations_count,  # Yeni eklendi
    }
    return render(request, 'dashboard/dashboard.html', context)

def get_performance_data(user):
    """30 günlük performans verileri"""
    import json
    from django.db.models import Count, Sum
    from django.utils import timezone
    from datetime import timedelta
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Günlük istatistikleri al
    dates = []
    sent_data = []
    open_data = []
    click_data = []
    
    current_date = start_date
    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)
        
        # O gün gönderilen toplam e-posta sayısı
        daily_sent = Campaign.objects.filter(
            user=user,
            sent_at__date=current_date
        ).aggregate(total=Sum('total_sent'))['total'] or 0
        
        # O gün açılan toplam e-posta sayısı
        daily_opens = Campaign.objects.filter(
            user=user,
            sent_at__date=current_date
        ).aggregate(total=Sum('opens'))['total'] or 0
        
        # O gün tıklanan toplam link sayısı
        daily_clicks = Campaign.objects.filter(
            user=user,
            sent_at__date=current_date
        ).aggregate(total=Sum('clicks'))['total'] or 0
        
        dates.append(current_date.strftime('%d %b'))
        sent_data.append(daily_sent)
        open_data.append(daily_opens)
        click_data.append(daily_clicks)
        
        current_date = next_date
    
    return {
        'dates': json.dumps(dates),
        'sent_data': json.dumps(sent_data),
        'open_data': json.dumps(open_data),
        'click_data': json.dumps(click_data),
    }

# views.py'ye ekle
# views.py - API güncellemesi
@login_required
def api_real_time_stats(request):
    """Gerçek zamanlı istatistikler API"""
    from django.utils import timezone
    from datetime import datetime, timedelta
    from django.db.models import Sum, Avg
    
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Aylık gönderim
    monthly_sent = Campaign.objects.filter(
        user=request.user,
        sent_at__date__gte=month_start
    ).aggregate(total=Sum('total_sent'))['total'] or 0
    
    # Ortalama açılma oranı
    avg_open_rate = Campaign.objects.filter(
        user=request.user,
        total_sent__gt=0
    ).aggregate(avg=Avg('opens'))['avg'] or 0
    avg_open_rate = round(avg_open_rate, 1) if avg_open_rate else 0
    
    # Günlük kota (basit hesaplama)
    daily_quota = 1000  # Varsayılan kota
    
    return JsonResponse({
        'monthly_sent': monthly_sent,
        'daily_quota': daily_quota,
        'avg_open_rate': f"{avg_open_rate}%",
        'timestamp': datetime.now().isoformat()
    })

# views.py - Delete view'larını güncelle
@login_required
def delete_mail_list(request, list_id):
    """Mail listesi sil"""
    mail_list = get_object_or_404(MailList, id=list_id, user=request.user)
    
    if request.method == 'POST':
        mail_list_name = mail_list.name
        mail_list.delete()
        messages.success(request, f'"{mail_list_name}" listesi başarıyla silindi!')
        return redirect('mail_lists')
    
    return render(request, 'dashboard/delete_mail_list.html', {'mail_list': mail_list})

@login_required
def delete_subscriber(request, subscriber_id):
    """Abone sil"""
    subscriber = get_object_or_404(Subscriber, id=subscriber_id, mail_list__user=request.user)
    
    if request.method == 'POST':
        subscriber_email = subscriber.email
        mail_list_id = subscriber.mail_list.id
        subscriber.delete()
        messages.success(request, f'"{subscriber_email}" abonesi başarıyla silindi!')
        return redirect('mail_list_detail', list_id=mail_list_id)
    
    return render(request, 'dashboard/delete_subscriber.html', {'subscriber': subscriber})

@login_required
def delete_campaign(request, campaign_id):
    """Kampanya sil"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    if request.method == 'POST':
        campaign_name = campaign.name
        campaign.delete()
        messages.success(request, f'"{campaign_name}" kampanyası başarıyla silindi!')
        return redirect('campaigns')
    
    return render(request, 'dashboard/delete_campaign.html', {'campaign': campaign})

@login_required
def delete_automation(request, automation_id):
    """Otomasyon sil"""
    automation = get_object_or_404(Automation, id=automation_id, user=request.user)
    
    if request.method == 'POST':
        automation_name = automation.name
        automation.delete()
        messages.success(request, f'"{automation_name}" otomasyonu başarıyla silindi!')
        return redirect('automations')
    
    return render(request, 'dashboard/delete_automation.html', {'automation': automation})

@login_required
def delete_template(request, template_id):
    """Şablon sil"""
    template = get_object_or_404(EmailTemplate, id=template_id, user=request.user)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'"{template_name}" şablonu başarıyla silindi!')
        return redirect('templates')
    
    return render(request, 'dashboard/delete_template.html', {'template': template})

@login_required
def remove_from_blacklist(request, blacklist_id):
    """Kara listeden çıkar"""
    blacklist_entry = get_object_or_404(Blacklist, id=blacklist_id, user=request.user)
    
    if request.method == 'POST':
        email = blacklist_entry.email
        blacklist_entry.delete()
        messages.success(request, f'"{email}" e-posta adresi kara listeden çıkarıldı!')
        return redirect('blacklist')
    
    return render(request, 'dashboard/remove_from_blacklist.html', {'blacklist_entry': blacklist_entry})

@login_required
def delete_webhook(request, webhook_id):
    """Webhook sil"""
    webhook = get_object_or_404(Webhook, id=webhook_id, user=request.user)
    
    if request.method == 'POST':
        webhook_name = webhook.name
        webhook.delete()
        messages.success(request, f'"{webhook_name}" webhook\'u başarıyla silindi!')
        return redirect('webhooks')
    
    return render(request, 'dashboard/delete_webhook.html', {'webhook': webhook})

@login_required
def add_automation_step(request, automation_id):
    """Otomasyona yeni adım ekle"""
    automation = get_object_or_404(Automation, id=automation_id, user=request.user)
    
    if request.method == 'POST':
        step_order = request.POST.get('step_order')
        campaign_id = request.POST.get('campaign')
        delay_days = request.POST.get('delay_days', 0)
        
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=request.user)
            
            AutomationStep.objects.create(
                automation=automation,
                step_order=step_order,
                campaign=campaign,
                delay_days=delay_days
            )
            
            messages.success(request, 'Adım başarıyla eklendi!')
            return redirect('edit_automation', automation_id=automation.id)
            
        except Campaign.DoesNotExist:
            messages.error(request, 'Geçersiz kampanya seçildi!')
    
    return redirect('edit_automation', automation_id=automation.id)

@login_required
def edit_automation_step(request, step_id):
    """Otomasyon adımını düzenle"""
    step = get_object_or_404(AutomationStep, id=step_id, automation__user=request.user)
    
    if request.method == 'POST':
        step.step_order = request.POST.get('step_order')
        step.delay_days = request.POST.get('delay_days', 0)
        
        campaign_id = request.POST.get('campaign')
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=request.user)
            step.campaign = campaign
        except Campaign.DoesNotExist:
            messages.error(request, 'Geçersiz kampanya seçildi!')
            return redirect('edit_automation', automation_id=step.automation.id)
        
        step.save()
        messages.success(request, 'Adım başarıyla güncellendi!')
    
    return redirect('edit_automation', automation_id=step.automation.id)

@login_required
def delete_automation_step(request, step_id):
    """Otomasyon adımını sil"""
    step = get_object_or_404(AutomationStep, id=step_id, automation__user=request.user)
    automation_id = step.automation.id
    
    if request.method == 'POST':
        step.delete()
        messages.success(request, 'Adım başarıyla silindi!')
        return redirect('edit_automation', automation_id=automation_id)
    
    return redirect('edit_automation', automation_id=automation_id)

# Mail List Views
@login_required
def mail_lists(request):
    """Mail listeleri sayfası"""
    lists = MailList.objects.filter(user=request.user)
    return render(request, 'dashboard/mail_lists.html', {'lists': lists})

@login_required
def create_mail_list(request):
    """Yeni mail listesi oluştur"""
    if request.method == 'POST':
        form = MailListForm(request.POST)
        if form.is_valid():
            mail_list = form.save(commit=False)
            mail_list.user = request.user
            mail_list.save()
            messages.success(request, 'Mail listesi başarıyla oluşturuldu!')
            return redirect('mail_lists')
    else:
        form = MailListForm()
    
    return render(request, 'dashboard/create_mail_list.html', {'form': form})

@login_required
def mail_list_detail(request, list_id):
    """Mail listesi detay"""
    mail_list = get_object_or_404(MailList, id=list_id, user=request.user)
    subscribers = mail_list.subscribers.filter(is_active=True)
    
    # Sayfalama
    paginator = Paginator(subscribers, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard/mail_list_detail.html', {
        'mail_list': mail_list,
        'page_obj': page_obj
    })

@login_required
def edit_mail_list(request, list_id):
    """Mail listesi düzenle"""
    mail_list = get_object_or_404(MailList, id=list_id, user=request.user)
    
    if request.method == 'POST':
        form = MailListForm(request.POST, instance=mail_list)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mail listesi başarıyla güncellendi!')
            return redirect('mail_lists')
    else:
        form = MailListForm(instance=mail_list)
    
    return render(request, 'dashboard/edit_mail_list.html', {
        'form': form,
        'mail_list': mail_list
    })


@login_required
def import_subscribers(request, list_id):
    """CSV'den abone içe aktar"""
    mail_list = get_object_or_404(MailList, id=list_id, user=request.user)
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        imported_count = 0
        skipped_count = 0
        
        for row in reader:
            email = row.get('email', '').strip()
            name = row.get('name', '').strip()
            
            if email:
                # E-posta zaten var mı kontrol et
                if not Subscriber.objects.filter(mail_list=mail_list, email=email).exists():
                    Subscriber.objects.create(
                        mail_list=mail_list,
                        email=email,
                        name=name
                    )
                    imported_count += 1
                else:
                    skipped_count += 1
        
        # Abone sayısını güncelle
        mail_list.update_counts()
        
        messages.success(request, f'{imported_count} abone başarıyla eklendi. {skipped_count} abone atlandı (zaten mevcut).')
        return redirect('mail_list_detail', list_id=mail_list.id)
    
    return render(request, 'dashboard/import_subscribers.html', {'mail_list': mail_list})

@login_required
def export_subscribers(request, list_id):
    """Aboneleri CSV'ye dışa aktar"""
    mail_list = get_object_or_404(MailList, id=list_id, user=request.user)
    subscribers = mail_list.subscribers.filter(is_active=True)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{mail_list.name}_aboneler.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Email', 'Ad Soyad', 'Telefon', 'Şirket', 'Abonelik Tarihi'])
    
    for subscriber in subscribers:
        writer.writerow([
            subscriber.email,
            subscriber.name,
            subscriber.phone,
            subscriber.company,
            subscriber.subscribed_at.strftime('%d.%m.%Y')
        ])
    
    return response

# Subscriber Views
@login_required
def add_subscriber(request):
    """Yeni abone ekle"""
    if request.method == 'POST':
        form = SubscriberForm(request.POST, user=request.user)
        if form.is_valid():
            subscriber = form.save()
            messages.success(request, 'Abone başarıyla eklendi!')
            return redirect('mail_list_detail', list_id=subscriber.mail_list.id)
    else:
        form = SubscriberForm(user=request.user)
    
    return render(request, 'dashboard/add_subscriber.html', {'form': form})

@login_required
def edit_subscriber(request, subscriber_id):
    """Abone düzenle"""
    subscriber = get_object_or_404(Subscriber, id=subscriber_id, mail_list__user=request.user)
    
    if request.method == 'POST':
        form = SubscriberForm(request.POST, instance=subscriber, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Abone başarıyla güncellendi!')
            return redirect('mail_list_detail', list_id=subscriber.mail_list.id)
    else:
        form = SubscriberForm(instance=subscriber, user=request.user)
    
    return render(request, 'dashboard/edit_subscriber.html', {
        'form': form,
        'subscriber': subscriber
    })



@login_required
def manual_unsubscribe(request, subscriber_id):
    """Manuel abonelikten çıkarma"""
    subscriber = get_object_or_404(Subscriber, id=subscriber_id, mail_list__user=request.user)
    
    if request.method == 'POST':
        subscriber.unsubscribe()
        messages.success(request, 'Abone başarıyla abonelikten çıkarıldı!')
        return redirect('mail_list_detail', list_id=subscriber.mail_list.id)
    
    return render(request, 'dashboard/manual_unsubscribe.html', {'subscriber': subscriber})

# Campaign Views
@login_required
def campaigns(request):
    """Kampanyalar listesi"""
    campaigns_list = Campaign.objects.filter(user=request.user).order_by('-created_at')
    
    # Sayfalama
    paginator = Paginator(campaigns_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard/campaigns.html', {'page_obj': page_obj})

@login_required
def create_campaign(request):
    """Yeni kampanya oluştur"""
    if request.method == 'POST':
        form = CampaignForm(request.POST, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user
            campaign.save()
            form.save_m2m()  # Many-to-many ilişkilerini kaydet
            
            messages.success(request, 'Kampanya başarıyla oluşturuldu!')
            return redirect('campaigns')
    else:
        form = CampaignForm(user=request.user)
    
    return render(request, 'dashboard/create_campaign.html', {'form': form})

@login_required
def campaign_detail(request, campaign_id):
    """Kampanya detay"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    return render(request, 'dashboard/campaign_detail.html', {'campaign': campaign})

@login_required
def edit_campaign(request, campaign_id):
    """Kampanya düzenle"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kampanya başarıyla güncellendi!')
            return redirect('campaigns')
    else:
        form = CampaignForm(instance=campaign, user=request.user)
    
    return render(request, 'dashboard/edit_campaign.html', {
        'form': form,
        'campaign': campaign
    })


# views.py - Send campaign ve test email views
@login_required
def send_campaign(request, campaign_id):
    """Kampanyayı hemen gönder"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Toplam abone sayısını kontrol et
            total_subscribers = 0
            for mail_list in campaign.mail_lists.all():
                total_subscribers += mail_list.subscribers.filter(is_active=True).count()
            
            if total_subscribers == 0:
                messages.error(request, 'Bu kampanya için hedef listede aktif abone bulunamadı!')
                return redirect('campaign_detail', campaign_id=campaign.id)
            
            # Asenkron olarak e-postaları gönder
            from .email_backend import send_campaign_async
            send_campaign_async(campaign.id)
            
            messages.success(request, f'Kampanya gönderimi başlatıldı! {total_subscribers} aboneye e-postalar arka planda gönderiliyor.')
            return redirect('campaigns')
            
        except Exception as e:
            messages.error(request, f'Gönderim sırasında hata oluştu: {str(e)}')
            return redirect('campaign_detail', campaign_id=campaign.id)
    
    # Toplam abone sayısını hesapla
    total_subscribers = 0
    for mail_list in campaign.mail_lists.all():
        total_subscribers += mail_list.subscribers.filter(is_active=True).count()
    
    return render(request, 'dashboard/send_campaign.html', {
        'campaign': campaign,
        'total_subscribers': total_subscribers
    })

# views.py - Real-time campaign stats API
@login_required
def api_campaign_stats(request, campaign_id):
    """Kampanya real-time istatistikleri"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    # Son 1 saatteki açılma ve tıklanma sayıları
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    
    recent_opens = campaign.logs.filter(
        status='opened',
        opened_at__gte=one_hour_ago
    ).count()
    
    recent_clicks = campaign.logs.filter(
        status='clicked', 
        clicked_at__gte=one_hour_ago
    ).count()
    
    return JsonResponse({
        'recent_opens': recent_opens,
        'recent_clicks': recent_clicks,
        'total_opens': campaign.unique_opens,
        'total_clicks': campaign.unique_clicks,
        'timestamp': timezone.now().isoformat()
    })

@login_required
def send_test_email(request, campaign_id):
    """Test e-postası gönder"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    if request.method == 'POST':
        test_email = request.POST.get('test_email')
        
        if not test_email:
            return JsonResponse({'success': False, 'message': 'Test e-posta adresi gerekli'})
        
        try:
            from .email_backend import EmailSender
            email_sender = EmailSender()
            
            success, message = email_sender.send_test_email(
                test_email,
                f"TEST: {campaign.subject}",
                campaign.content
            )
            
            if success:
                return JsonResponse({'success': True, 'message': 'Test e-postası başarıyla gönderildi!'})
            else:
                return JsonResponse({'success': False, 'message': message})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Hata: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Geçersiz istek'})

@login_required
def schedule_campaign(request, campaign_id):
    """Kampanyayı planla"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    if request.method == 'POST':
        scheduled_time = request.POST.get('scheduled_time')
        if scheduled_time:
            campaign.scheduled_time = scheduled_time
            campaign.status = 'scheduled'
            campaign.save()
            messages.success(request, 'Kampanya başarıyla planlandı!')
        else:
            messages.error(request, 'Lütfen geçerli bir tarih seçin.')
        
        return redirect('campaigns')
    
    return render(request, 'dashboard/schedule_campaign.html', {'campaign': campaign})

@login_required
def campaign_stats(request, campaign_id):
    """Kampanya istatistikleri"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    stats = {
        'sent': campaign.total_sent,
        'delivered': campaign.delivered,
        'opens': campaign.opens,
        'unique_opens': campaign.unique_opens,
        'clicks': campaign.clicks,
        'unique_clicks': campaign.unique_clicks,
        'bounces': campaign.bounces,
        'complaints': campaign.complaints,
        'unsubscribes': campaign.unsubscribes,
        'open_rate': campaign.get_open_rate(),
        'click_rate': campaign.get_click_rate(),
        'bounce_rate': campaign.get_bounce_rate(),
    }
    
    return render(request, 'dashboard/campaign_stats.html', {
        'campaign': campaign,
        'stats': stats
    })

@login_required
def duplicate_campaign(request, campaign_id):
    """Kampanyayı kopyala"""
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    
    if request.method == 'POST':
        # Kampanyayı kopyala
        campaign.pk = None
        campaign.name = f"{campaign.name} (Kopya)"
        campaign.status = 'draft'
        campaign.total_sent = 0
        campaign.opens = 0
        campaign.clicks = 0
        campaign.bounces = 0
        campaign.sent_at = None
        campaign.save()
        
        # Many-to-many ilişkilerini kopyala
        campaign.mail_lists.set(campaign.mail_lists.all())
        
        messages.success(request, 'Kampanya başarıyla kopyalandı!')
        return redirect('campaigns')
    
    return render(request, 'dashboard/duplicate_campaign.html', {'campaign': campaign})

# Automation Views
@login_required
def automations(request):
    """Otomasyonlar listesi"""
    automations_list = Automation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/automations.html', {'automations': automations_list})

@login_required
def create_automation(request):
    """Yeni otomasyon oluştur"""
    if request.method == 'POST':
        form = AutomationForm(request.POST, user=request.user)
        if form.is_valid():
            automation = form.save(commit=False)
            automation.user = request.user
            automation.save()
            messages.success(request, 'Otomasyon başarıyla oluşturuldu!')
            return redirect('automations')
    else:
        form = AutomationForm(user=request.user)
    
    return render(request, 'dashboard/create_automation.html', {'form': form})

@login_required
def automation_detail(request, automation_id):
    """Otomasyon detay"""
    automation = get_object_or_404(Automation, id=automation_id, user=request.user)
    steps = automation.steps.all().order_by('step_order')
    
    return render(request, 'dashboard/automation_detail.html', {
        'automation': automation,
        'steps': steps
    })

@login_required
def edit_automation(request, automation_id):
    """Otomasyon düzenle"""
    automation = get_object_or_404(Automation, id=automation_id, user=request.user)
    
    if request.method == 'POST':
        form = AutomationForm(request.POST, instance=automation, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Otomasyon başarıyla güncellendi!')
            return redirect('automations')
    else:
        form = AutomationForm(instance=automation, user=request.user)
    
    return render(request, 'dashboard/edit_automation.html', {
        'form': form,
        'automation': automation
    })


@login_required
def toggle_automation(request, automation_id):
    """Otomasyon aktif/pasif toggle"""
    automation = get_object_or_404(Automation, id=automation_id, user=request.user)
    
    automation.is_active = not automation.is_active
    automation.save()
    
    status = "aktif" if automation.is_active else "pasif"
    messages.success(request, f'Otomasyon {status} hale getirildi!')
    return redirect('automations')

# Analytics Views
@login_required
def analytics(request):
    """Analitik ana sayfa"""
    return redirect('analytics_overview')

@login_required
def analytics_overview(request):
    """Analitik genel bakış"""
    # 30 günlük istatistikler
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=30)
    
    campaigns = Campaign.objects.filter(
        user=request.user,
        sent_at__range=[start_date, end_date]
    )
    
    total_emails_sent = sum(c.total_sent for c in campaigns)
    total_opens = sum(c.opens for c in campaigns)
    total_clicks = sum(c.clicks for c in campaigns)
    
    open_rate = (total_opens / total_emails_sent * 100) if total_emails_sent > 0 else 0
    click_rate = (total_clicks / total_emails_sent * 100) if total_emails_sent > 0 else 0
    
    context = {
        'total_emails_sent': total_emails_sent,
        'total_opens': total_opens,
        'total_clicks': total_clicks,
        'open_rate': round(open_rate, 2),
        'click_rate': round(click_rate, 2),
        'period': '30 gün'
    }
    return render(request, 'dashboard/analytics_overview.html', context)

@login_required
def analytics_campaigns(request):
    """Kampanya analitikleri"""
    campaigns = Campaign.objects.filter(user=request.user).order_by('-sent_at')
    return render(request, 'dashboard/analytics_campaigns.html', {'campaigns': campaigns})

@login_required
def analytics_subscribers(request):
    """Abone analitikleri"""
    mail_lists = MailList.objects.filter(user=request.user)
    
    total_subscribers = sum(ml.subscriber_count for ml in mail_lists)
    total_unsubscribed = sum(ml.unsubscribed_count for ml in mail_lists)
    
    # Son 30 gündeki yeni aboneler
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    new_subscribers = Subscriber.objects.filter(
        mail_list__user=request.user,
        subscribed_at__gte=thirty_days_ago
    ).count()
    
    context = {
        'total_subscribers': total_subscribers,
        'total_unsubscribed': total_unsubscribed,
        'new_subscribers': new_subscribers,
        'mail_lists': mail_lists
    }
    return render(request, 'dashboard/analytics_subscribers.html', context)

# Profile & Settings Views
@login_required
def profile(request):
    """Kullanıcı profili"""
    return render(request, 'dashboard/profile.html')

@login_required
def edit_profile(request):
    """Profil düzenle"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil başarıyla güncellendi!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'dashboard/edit_profile.html', {'form': form})

@login_required
def settings(request):
    """Genel ayarlar"""
    return render(request, 'dashboard/settings.html')

@login_required
def email_settings(request):
    """E-posta ayarları"""
    return render(request, 'dashboard/email_settings.html')

@login_required
def api_settings(request):
    """API ayarları"""
    return render(request, 'dashboard/api_settings.html')

# Template Views
@login_required
def templates(request):
    """Şablonlar listesi"""
    templates_list = EmailTemplate.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/templates.html', {'templates': templates_list})

@login_required
def create_template(request):
    """Yeni şablon oluştur"""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()
            messages.success(request, 'Şablon başarıyla oluşturuldu!')
            return redirect('templates')
    else:
        form = EmailTemplateForm(user=request.user)
    
    return render(request, 'dashboard/create_template.html', {'form': form})

@login_required
def edit_template(request, template_id):
    """Şablon düzenle"""
    template = get_object_or_404(EmailTemplate, id=template_id, user=request.user)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Şablon başarıyla güncellendi!')
            return redirect('templates')
    else:
        form = EmailTemplateForm(instance=template, user=request.user)
    
    return render(request, 'dashboard/edit_template.html', {
        'form': form,
        'template': template
    })


# Blacklist Views
@login_required
def blacklist(request):
    """Kara liste"""
    blacklist_entries = Blacklist.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/blacklist.html', {'blacklist_entries': blacklist_entries})

@login_required
def add_to_blacklist(request):
    """Kara listeye ekle"""
    if request.method == 'POST':
        form = BlacklistForm(request.POST, user=request.user)
        if form.is_valid():
            blacklist_entry = form.save(commit=False)
            blacklist_entry.user = request.user
            blacklist_entry.save()
            messages.success(request, 'E-posta kara listeye eklendi!')
            return redirect('blacklist')
    else:
        form = BlacklistForm(user=request.user)
    
    return render(request, 'dashboard/add_to_blacklist.html', {'form': form})

@login_required
def remove_from_blacklist(request, blacklist_id):
    """Kara listeden çıkar"""
    blacklist_entry = get_object_or_404(Blacklist, id=blacklist_id, user=request.user)
    
    if request.method == 'POST':
        blacklist_entry.delete()
        messages.success(request, 'E-posta kara listeden çıkarıldı!')
        return redirect('blacklist')
    
    return render(request, 'dashboard/remove_from_blacklist.html', {'blacklist_entry': blacklist_entry})

# Webhook Views
@login_required
def webhooks(request):
    """Webhook'lar"""
    webhooks_list = Webhook.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/webhooks.html', {'webhooks': webhooks_list})

@login_required
def create_webhook(request):
    """Yeni webhook oluştur"""
    if request.method == 'POST':
        form = WebhookForm(request.POST, user=request.user)
        if form.is_valid():
            webhook = form.save(commit=False)
            webhook.user = request.user
            webhook.save()
            messages.success(request, 'Webhook başarıyla oluşturuldu!')
            return redirect('webhooks')
    else:
        form = WebhookForm(user=request.user)
    
    return render(request, 'dashboard/create_webhook.html', {'form': form})

@login_required
def edit_webhook(request, webhook_id):
    """Webhook düzenle"""
    webhook = get_object_or_404(Webhook, id=webhook_id, user=request.user)
    
    if request.method == 'POST':
        form = WebhookForm(request.POST, instance=webhook, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Webhook başarıyla güncellendi!')
            return redirect('webhooks')
    else:
        form = WebhookForm(instance=webhook, user=request.user)
    
    return render(request, 'dashboard/edit_webhook.html', {
        'form': form,
        'webhook': webhook
    })


@login_required
def test_webhook(request, webhook_id):
    """Webhook test et"""
    webhook = get_object_or_404(Webhook, id=webhook_id, user=request.user)
    
    # Burada webhook test işlemi yapılacak
    messages.info(request, 'Webhook test işlemi geliştirme aşamasındadır.')
    return redirect('webhooks')

# API Views
@login_required
def api_campaigns(request):
    """Kampanya API"""
    campaigns = Campaign.objects.filter(user=request.user)
    data = {
        'campaigns': [
            {
                'id': str(campaign.id),
                'name': campaign.name,
                'status': campaign.status,
                'sent_at': campaign.sent_at.isoformat() if campaign.sent_at else None
            }
            for campaign in campaigns
        ]
    }
    return JsonResponse(data)

@login_required
def api_subscribers(request):
    """Abone API"""
    mail_list_id = request.GET.get('mail_list_id')
    if mail_list_id:
        subscribers = Subscriber.objects.filter(
            mail_list__id=mail_list_id,
            mail_list__user=request.user
        )
    else:
        subscribers = Subscriber.objects.filter(mail_list__user=request.user)
    
    data = {
        'subscribers': [
            {
                'id': str(subscriber.id),
                'email': subscriber.email,
                'name': subscriber.name,
                'mail_list': subscriber.mail_list.name
            }
            for subscriber in subscribers[:100]  # Limit to 100 results
        ]
    }
    return JsonResponse(data)

@login_required
def api_analytics(request):
    """Analitik API"""
    # Basit analitik verisi
    campaigns = Campaign.objects.filter(user=request.user)
    
    data = {
        'total_campaigns': campaigns.count(),
        'total_emails_sent': sum(c.total_sent for c in campaigns),
        'average_open_rate': round(
            sum(c.get_open_rate() for c in campaigns) / campaigns.count() if campaigns.count() > 0 else 0, 
            2
        )
    }
    return JsonResponse(data)

# Utility Views
@login_required
def get_ai_subject_suggestion(request):
    """AI konu önerisi"""
    content = request.GET.get('content', '')
    
    # Basit anahtar kelime bazlı öneriler
    suggestions = [
        f"Önemli Güncelleme: {content[:30]}...",
        f"Bunu kaçırmayın: {content[:25]}...",
        f"Özel teklifimiz var!",
        f"Son fırsat: {content[:20]}...",
        f"Merhaba, {content[:15]} hakkında...",
        f"🎯 {content[:25]}...",
        f"🚀 {content[:20]} için özel içerik",
        f"Ücretsiz: {content[:15]} rehberi"
    ]
    
    return JsonResponse({'suggestions': suggestions})

@login_required
def validate_email(request):
    """E-posta validasyon"""
    email = request.GET.get('email', '')
    
    # Basit e-posta validasyonu
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email))
    
    return JsonResponse({'valid': is_valid})

@login_required
def upload_image(request):
    """Resim yükleme"""
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        # Burada resim işleme ve kaydetme yapılacak
        messages.success(request, 'Resim başarıyla yüklendi!')
        return JsonResponse({'success': True, 'url': '/media/uploads/' + image.name})
    
    return JsonResponse({'success': False, 'error': 'Resim yüklenemedi'})

# Tracking Views
# views.py - Tracking view'larını güncelle
from django.http import HttpResponse
import base64
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def track_open(request, subscriber_id, campaign_id):
    """E-posta açılma takibi"""
    try:
        subscriber = Subscriber.objects.get(id=subscriber_id)
        campaign = Campaign.objects.get(id=campaign_id)
        
        # EmailLog kaydını bul veya oluştur
        email_log, created = EmailLog.objects.get_or_create(
            campaign=campaign,
            subscriber=subscriber,
            defaults={
                'status': 'sent',
                'message_id': f"{campaign_id}_{subscriber_id}"
            }
        )
        
        # Sadece ilk açılmada say
        if email_log.status != 'opened':
            email_log.status = 'opened'
            email_log.opened_at = timezone.now()
            email_log.user_agent = request.META.get('HTTP_USER_AGENT', '')
            email_log.ip_address = get_client_ip(request)
            email_log.save()
            
            # Kampanya istatistiklerini güncelle
            campaign.opens += 1
            campaign.unique_opens = EmailLog.objects.filter(
                campaign=campaign, 
                status='opened'
            ).values('subscriber').distinct().count()
            campaign.save()
            
            print(f"E-posta açıldı: {subscriber.email} - {campaign.name}")
        
        # 1x1 transparent GIF döndür
        gif_data = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        response = HttpResponse(gif_data, content_type='image/gif')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
        
    except (Subscriber.DoesNotExist, Campaign.DoesNotExist):
        # Hata durumunda yine de GIF döndür (hata vermesin)
        gif_data = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        return HttpResponse(gif_data, content_type='image/gif')

@csrf_exempt
def track_click(request, subscriber_id, campaign_id):
    """E-posta tıklanma takibi"""
    try:
        subscriber = Subscriber.objects.get(id=subscriber_id)
        campaign = Campaign.objects.get(id=campaign_id)
        original_url = request.GET.get('url', '')
        
        if not original_url:
            return redirect('/')
        
        # EmailLog kaydını bul veya oluştur
        email_log, created = EmailLog.objects.get_or_create(
            campaign=campaign,
            subscriber=subscriber,
            defaults={
                'status': 'sent',
                'message_id': f"{campaign_id}_{subscriber_id}"
            }
        )
        
        # Tıklanma kaydı oluştur
        click_track, created = ClickTrack.objects.get_or_create(
            email_log=email_log,
            url=original_url,
            defaults={'click_count': 1}
        )
        
        if not created:
            click_track.click_count += 1
            click_track.save()
        
        # EmailLog durumunu güncelle
        if email_log.status != 'clicked':
            email_log.status = 'clicked'
            email_log.clicked_at = timezone.now()
            email_log.user_agent = request.META.get('HTTP_USER_AGENT', '')
            email_log.ip_address = get_client_ip(request)
            email_log.save()
            
            # Kampanya istatistiklerini güncelle
            campaign.clicks += 1
            campaign.unique_clicks = EmailLog.objects.filter(
                campaign=campaign, 
                status='clicked'
            ).values('subscriber').distinct().count()
            campaign.save()
            
            print(f"Link tıklandı: {subscriber.email} - {original_url}")
        
        # Orijinal URL'ye yönlendir
        return redirect(original_url)
        
    except (Subscriber.DoesNotExist, Campaign.DoesNotExist):
        # Hata durumunda orijinal URL'ye yönlendir
        return redirect(original_url)

def get_client_ip(request):
    """İstemci IP adresini al"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def unsubscribe(request, subscriber_id, campaign_id):
    """Abonelikten çıkarma"""
    try:
        subscriber = Subscriber.objects.get(id=subscriber_id)
        campaign = Campaign.objects.get(id=campaign_id)
        
        if request.method == 'POST':
            subscriber.unsubscribe()
            return render(request, 'dashboard/unsubscribe_success.html')
        
        return render(request, 'dashboard/unsubscribe_confirm.html', {
            'subscriber': subscriber,
            'campaign': campaign
        })
    
    except (Subscriber.DoesNotExist, Campaign.DoesNotExist):
        return render(request, 'dashboard/unsubscribe_error.html')

# Error Views
def custom_404_view(request, exception):
    """404 hata sayfası"""
    return render(request, 'errors/404.html', status=404)

def custom_500_view(request):
    """500 hata sayfası"""
    return render(request, 'errors/500.html', status=500)