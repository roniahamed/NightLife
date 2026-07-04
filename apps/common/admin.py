from django.contrib import admin
from .models import PlatformSettings

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
