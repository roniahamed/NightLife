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

class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.IntegerField(default=0, help_text="Order in which FAQ is displayed (lower is first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question

class LegalDocument(models.Model):
    DOCUMENT_TYPES = (
        ('terms', 'Terms of Service'),
        ('privacy', 'Privacy Policy'),
        ('guidelines', 'Community Guidelines'),
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, unique=True)
    content = models.TextField(help_text="Content of the document (Markdown/HTML supported)")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return dict(self.DOCUMENT_TYPES).get(self.document_type, self.document_type)

class BugReport(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    )
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='bug_reports')
    description = models.TextField(help_text="Description of the bug")
    steps_to_reproduce = models.TextField(blank=True, help_text="Steps to reproduce the bug")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_display = self.user.email if self.user else "Anonymous"
        return f"Bug Report from {user_display} - {self.status}"
