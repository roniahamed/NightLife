from django.contrib import admin
from .models import PlatformSettings, FAQ, TermsAndCondition, PrivacyPolicy, CommunityGuideline, BugReport

@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ticket_commission_percentage')
    
    def has_add_permission(self, request):
        # Prevent adding more than one instance
        if PlatformSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the singleton
        return False

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'updated_at')
    search_fields = ('question',)
    ordering = ('order', '-created_at')

@admin.register(TermsAndCondition)
class TermsAndConditionAdmin(admin.ModelAdmin):
    list_display = ('id', 'updated_at')
    search_fields = ('content',)

@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'updated_at')
    search_fields = ('content',)

@admin.register(CommunityGuideline)
class CommunityGuidelineAdmin(admin.ModelAdmin):
    list_display = ('id', 'updated_at')
    search_fields = ('content',)

@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('description', 'user__email', 'user__username')
    ordering = ('-created_at',)
