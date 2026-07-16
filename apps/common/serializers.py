from rest_framework import serializers
from .models import FAQ, TermsAndCondition, PrivacyPolicy, CommunityGuideline, BugReport

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ('id', 'question', 'answer', 'order', 'updated_at')

class TermsAndConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndCondition
        fields = ('id', 'content', 'updated_at')
        read_only_fields = ('id', 'updated_at')

class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ('id', 'content', 'updated_at')
        read_only_fields = ('id', 'updated_at')

class CommunityGuidelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityGuideline
        fields = ('id', 'content', 'updated_at')
        read_only_fields = ('id', 'updated_at')

class BugReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugReport
        fields = ('id', 'description', 'steps_to_reproduce', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')
