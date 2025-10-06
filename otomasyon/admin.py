from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import *

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'phone', 'timezone']
    search_fields = ['user__username', 'user__email', 'phone']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'plan_type', 'max_subscribers']
    list_filter = ['plan_type']
    search_fields = ['name', 'domain']

@admin.register(MailList)
class MailListAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'list_type', 'subscriber_count', 'is_active']
    list_filter = ['list_type', 'is_active', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['subscriber_count', 'unsubscribed_count']

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'mail_list', 'name', 'is_active', 'is_verified', 'subscribed_at']
    list_filter = ['is_active', 'is_verified', 'mail_list', 'created_at']
    search_fields = ['email', 'name', 'mail_list__name']
    readonly_fields = ['subscribed_at', 'unsubscribed_at']

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'template_type', 'is_default', 'created_at']
    list_filter = ['template_type', 'is_default']
    search_fields = ['name', 'user__username']

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'total_sent', 'opens', 'clicks', 'created_at']
    list_filter = ['status', 'created_at', 'is_ab_test']
    search_fields = ['name', 'user__username', 'subject']
    readonly_fields = ['sent_at', 'total_sent', 'opens', 'clicks', 'bounces']
    filter_horizontal = ['mail_lists']

@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'trigger_type', 'is_active', 'total_triggered', 'created_at']
    list_filter = ['trigger_type', 'is_active']
    search_fields = ['name', 'user__username']

@admin.register(AutomationStep)
class AutomationStepAdmin(admin.ModelAdmin):
    list_display = ['automation', 'step_order', 'campaign', 'delay_days']
    list_filter = ['automation']
    ordering = ['automation', 'step_order']

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'subscriber', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['campaign__name', 'subscriber__email']
    readonly_fields = ['created_at', 'opened_at', 'clicked_at']

@admin.register(ClickTrack)
class ClickTrackAdmin(admin.ModelAdmin):
    list_display = ['email_log', 'url', 'click_count']
    list_filter = ['created_at']
    search_fields = ['email_log__subscriber__email', 'url']

@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ['email', 'user', 'reason', 'created_at']
    list_filter = ['reason', 'created_at']
    search_fields = ['email', 'user__username']

@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'event_type', 'is_active', 'created_at']
    list_filter = ['event_type', 'is_active']
    search_fields = ['name', 'user__username', 'url']

@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'emails_sent', 'open_rate', 'click_rate']
    list_filter = ['date']
    search_fields = ['user__username']
    readonly_fields = ['delivery_rate', 'open_rate', 'click_rate', 'bounce_rate']

# User admin'i genişletme
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']

# Mevcut User admin'ini kaldır ve yeniden kaydet
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)