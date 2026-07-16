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

class TermsAndCondition(models.Model):
    content = models.TextField(help_text="Content of the Terms and Conditions (Markdown/HTML supported)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Terms and Conditions"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Terms and Conditions (Updated: {self.updated_at.strftime('%Y-%m-%d')})"

class PrivacyPolicy(models.Model):
    content = models.TextField(help_text="Content of the Privacy Policy (Markdown/HTML supported)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Privacy Policies"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Privacy Policy (Updated: {self.updated_at.strftime('%Y-%m-%d')})"

class CommunityGuideline(models.Model):
    content = models.TextField(help_text="Content of the Community Guidelines (Markdown/HTML supported)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Community Guidelines"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Community Guidelines (Updated: {self.updated_at.strftime('%Y-%m-%d')})"

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
