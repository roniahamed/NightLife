from rest_framework import serializers
from .models import FAQ, LegalDocument, BugReport

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ('id', 'question', 'answer', 'order', 'updated_at')

class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ('document_type', 'content', 'updated_at')

class BugReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugReport
        fields = ('id', 'description', 'steps_to_reproduce', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')
