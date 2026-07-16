from django.urls import path
from .views import FAQListCreateView, LegalDocumentView, LegalDocumentListCreateView, ReportBugListCreateView

urlpatterns = [
    path('faqs/', FAQListCreateView.as_view(), name='faqs'),
    path('legal/', LegalDocumentListCreateView.as_view(), name='legal-documents'),
    path('legal/<str:document_type>/', LegalDocumentView.as_view(), name='legal-document'),
    path('report-bug/', ReportBugListCreateView.as_view(), name='report-bug'),
]
