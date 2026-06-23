from django.contrib import admin
from .models import User, UserOTP, UserFollow, UserBlock, UserReport, UserSettings

admin.site.register(User)
admin.site.register(UserOTP)
admin.site.register(UserFollow)
admin.site.register(UserBlock)
admin.site.register(UserReport)
admin.site.register(UserSettings)
