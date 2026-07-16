from django.urls import path
from .views import (
    FAQListCreateView,
    TermsAndConditionListCreateView,
    TermsAndConditionDetailView,
    PrivacyPolicyListCreateView,
    PrivacyPolicyDetailView,
    CommunityGuidelineListCreateView,
    CommunityGuidelineDetailView,
    ReportBugListCreateView
)

urlpatterns = [
    path('faqs/', FAQListCreateView.as_view(), name='faqs'),
    path('terms/', TermsAndConditionListCreateView.as_view(), name='terms'),
    path('terms/<int:pk>/', TermsAndConditionDetailView.as_view(), name='terms-detail'),
    path('privacy-policy/', PrivacyPolicyListCreateView.as_view(), name='privacy-policy'),
    path('privacy-policy/<int:pk>/', PrivacyPolicyDetailView.as_view(), name='privacy-policy-detail'),
    path('community-guidelines/', CommunityGuidelineListCreateView.as_view(), name='community-guidelines'),
    path('community-guidelines/<int:pk>/', CommunityGuidelineDetailView.as_view(), name='community-guidelines-detail'),
    path('report-bug/', ReportBugListCreateView.as_view(), name='report-bug'),
]
