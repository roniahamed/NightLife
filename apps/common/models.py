from django.db import models

class PlatformSettings(models.Model):
    ticket_commission_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=3.00,
        help_text="The percentage of ticket sales the platform takes as commission."
    )
    
    class Meta:
        verbose_name = "Platform Setting"
        verbose_name_plural = "Platform Settings"

    def __str__(self):
        return "Platform Settings"
    
    def save(self, *args, **kwargs):
        # Enforce singleton pattern
        if not self.pk and PlatformSettings.objects.exists():
            return
        super().save(*args, **kwargs)
