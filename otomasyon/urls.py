from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public URLs
    path('', views.index, name='index'),
    path('subscribe/', views.public_subscribe, name='public_subscribe'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='auth/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    
    path('register/', views.register, name='register'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/password_reset.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Mail List URLs
    path('dashboard/mail-lists/', views.mail_lists, name='mail_lists'),
    path('dashboard/mail-lists/create/', views.create_mail_list, name='create_mail_list'),
    path('dashboard/mail-lists/<uuid:list_id>/', views.mail_list_detail, name='mail_list_detail'),
    path('dashboard/mail-lists/<uuid:list_id>/edit/', views.edit_mail_list, name='edit_mail_list'),
    path('dashboard/mail-lists/<uuid:list_id>/delete/', views.delete_mail_list, name='delete_mail_list'),
    path('dashboard/mail-lists/<uuid:list_id>/import/', views.import_subscribers, name='import_subscribers'),
    path('dashboard/mail-lists/<uuid:list_id>/export/', views.export_subscribers, name='export_subscribers'),
    
    # Subscriber URLs
    path('dashboard/subscribers/add/', views.add_subscriber, name='add_subscriber'),
    path('dashboard/subscribers/<uuid:subscriber_id>/edit/', views.edit_subscriber, name='edit_subscriber'),
    path('dashboard/subscribers/<uuid:subscriber_id>/delete/', views.delete_subscriber, name='delete_subscriber'),
    path('dashboard/subscribers/<uuid:subscriber_id>/unsubscribe/', views.manual_unsubscribe, name='manual_unsubscribe'),
    
    # Campaign URLs
    path('dashboard/campaigns/', views.campaigns, name='campaigns'),
    path('dashboard/campaigns/create/', views.create_campaign, name='create_campaign'),
    path('dashboard/campaigns/<uuid:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('dashboard/campaigns/<uuid:campaign_id>/edit/', views.edit_campaign, name='edit_campaign'),
    path('dashboard/campaigns/<uuid:campaign_id>/delete/', views.delete_campaign, name='delete_campaign'),
    path('dashboard/campaigns/<uuid:campaign_id>/send/', views.send_campaign, name='send_campaign'),
    path('dashboard/campaigns/<uuid:campaign_id>/schedule/', views.schedule_campaign, name='schedule_campaign'),
    path('dashboard/campaigns/<uuid:campaign_id>/stats/', views.campaign_stats, name='campaign_stats'),
    path('dashboard/campaigns/<uuid:campaign_id>/duplicate/', views.duplicate_campaign, name='duplicate_campaign'),
    
    # Automation URLs
    path('dashboard/automations/', views.automations, name='automations'),
    path('dashboard/automations/create/', views.create_automation, name='create_automation'),
    path('dashboard/automations/<uuid:automation_id>/', views.automation_detail, name='automation_detail'),
    path('dashboard/automations/<uuid:automation_id>/edit/', views.edit_automation, name='edit_automation'),
    path('dashboard/automations/<uuid:automation_id>/delete/', views.delete_automation, name='delete_automation'),
    path('dashboard/automations/<uuid:automation_id>/toggle/', views.toggle_automation, name='toggle_automation'),
    
    # Analytics URLs
    path('dashboard/analytics/', views.analytics, name='analytics'),
    path('dashboard/analytics/overview/', views.analytics_overview, name='analytics_overview'),
    path('dashboard/analytics/campaigns/', views.analytics_campaigns, name='analytics_campaigns'),
    path('dashboard/analytics/subscribers/', views.analytics_subscribers, name='analytics_subscribers'),
    
    # Profile & Settings URLs
    path('dashboard/profile/', views.profile, name='profile'),
    path('dashboard/profile/edit/', views.edit_profile, name='edit_profile'),
    path('dashboard/settings/', views.settings, name='settings'),
    path('dashboard/settings/email/', views.email_settings, name='email_settings'),
    path('dashboard/settings/api/', views.api_settings, name='api_settings'),
    
    # Templates URLs
    path('dashboard/templates/', views.templates, name='templates'),
    path('dashboard/templates/create/', views.create_template, name='create_template'),
    path('dashboard/templates/<uuid:template_id>/edit/', views.edit_template, name='edit_template'),
    path('dashboard/templates/<uuid:template_id>/delete/', views.delete_template, name='delete_template'),
    
    # Blacklist URLs
    path('dashboard/blacklist/', views.blacklist, name='blacklist'),
    path('dashboard/blacklist/add/', views.add_to_blacklist, name='add_to_blacklist'),
    path('dashboard/blacklist/<uuid:blacklist_id>/delete/', views.remove_from_blacklist, name='remove_from_blacklist'),
    
    # Webhook URLs
    path('dashboard/webhooks/', views.webhooks, name='webhooks'),
    path('dashboard/webhooks/create/', views.create_webhook, name='create_webhook'),
    path('dashboard/webhooks/<uuid:webhook_id>/edit/', views.edit_webhook, name='edit_webhook'),
    path('dashboard/webhooks/<uuid:webhook_id>/delete/', views.delete_webhook, name='delete_webhook'),
    path('dashboard/webhooks/<uuid:webhook_id>/test/', views.test_webhook, name='test_webhook'),
    
    # API URLs
    path('dashboard/api/campaigns/', views.api_campaigns, name='api_campaigns'),
    path('dashboard/api/subscribers/', views.api_subscribers, name='api_subscribers'),
    path('dashboard/api/analytics/', views.api_analytics, name='api_analytics'),
    
    # Utility URLs
    path('dashboard/get-ai-subject-suggestion/', views.get_ai_subject_suggestion, name='get_ai_subject_suggestion'),
    path('dashboard/validate-email/', views.validate_email, name='validate_email'),
    path('dashboard/upload-image/', views.upload_image, name='upload_image'),
    
    # Tracking URLs (E-posta açılma ve tıklanma takibi için)
    path('track/open/<uuid:log_id>/', views.track_open, name='track_open'),
    path('track/click/<uuid:log_id>/', views.track_click, name='track_click'),
    path('unsubscribe/<uuid:subscriber_id>/<uuid:campaign_id>/', views.unsubscribe, name='unsubscribe'),
    path('dashboard/automations/steps/<uuid:automation_id>/add/', views.add_automation_step, name='add_automation_step'),
    path('dashboard/automations/steps/<uuid:step_id>/edit/', views.edit_automation_step, name='edit_automation_step'),
    path('dashboard/automations/steps/<uuid:step_id>/delete/', views.delete_automation_step, name='delete_automation_step'),
# urls.py'ye ekle
    path('dashboard/api/real-time-stats/', views.api_real_time_stats, name='api_real_time_stats'),
# urls.py'ye ekle
    path('dashboard/campaigns/<uuid:campaign_id>/test-send/', views.send_test_email, name='send_test_email'),
# urls.py'ye ekle
    path('dashboard/api/campaign-stats/<uuid:campaign_id>/', views.api_campaign_stats, name='api_campaign_stats'),
]