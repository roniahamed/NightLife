from rest_framework import generics, status, mixins
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from apps.common.utils import success_response, error_response
from .models import FAQ, TermsAndCondition, PrivacyPolicy, CommunityGuideline, BugReport
from .serializers import FAQSerializer, TermsAndConditionSerializer, PrivacyPolicySerializer, CommunityGuidelineSerializer, BugReportSerializer

class FAQListCreateView(generics.ListCreateAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get FAQs", description="Returns a list of all Frequently Asked Questions.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="FAQs retrieved successfully.")

    @extend_schema(summary="Create FAQ", description="Allows an admin to create a new FAQ.", tags=['Support'])
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="FAQ created successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class TermsAndConditionListCreateView(generics.ListCreateAPIView):
    queryset = TermsAndCondition.objects.all()
    serializer_class = TermsAndConditionSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get All Terms and Conditions", description="Retrieve all terms and conditions documents.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Terms and conditions retrieved successfully.")

    @extend_schema(summary="Create Terms and Conditions", description="Allows an admin to create a new terms document.", tags=['Support'])
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Terms created successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class TermsAndConditionDetailView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, generics.GenericAPIView):
    queryset = TermsAndCondition.objects.all()
    serializer_class = TermsAndConditionSerializer

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get Terms and Conditions", description="Retrieve terms and conditions by ID.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document)
        return success_response(data=serializer.data, message="Terms and conditions retrieved successfully.")

    @extend_schema(summary="Update Terms and Conditions (Partial)", description="Partially update existing terms (Admin only).", tags=['Support'])
    def patch(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Terms and conditions updated successfully.")
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class PrivacyPolicyListCreateView(generics.ListCreateAPIView):
    queryset = PrivacyPolicy.objects.all()
    serializer_class = PrivacyPolicySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get All Privacy Policies", description="Retrieve all privacy policies.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Privacy policies retrieved successfully.")

    @extend_schema(summary="Create Privacy Policy", description="Allows an admin to create a new privacy policy.", tags=['Support'])
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Privacy policy created successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class PrivacyPolicyDetailView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, generics.GenericAPIView):
    queryset = PrivacyPolicy.objects.all()
    serializer_class = PrivacyPolicySerializer

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get Privacy Policy", description="Retrieve a privacy policy by ID.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document)
        return success_response(data=serializer.data, message="Privacy policy retrieved successfully.")

    @extend_schema(summary="Update Privacy Policy (Partial)", description="Partially update an existing privacy policy (Admin only).", tags=['Support'])
    def patch(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Privacy policy updated successfully.")
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class CommunityGuidelineListCreateView(generics.ListCreateAPIView):
    queryset = CommunityGuideline.objects.all()
    serializer_class = CommunityGuidelineSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get All Community Guidelines", description="Retrieve all community guidelines.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Community guidelines retrieved successfully.")

    @extend_schema(summary="Create Community Guideline", description="Allows an admin to create a new community guideline.", tags=['Support'])
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Community guideline created successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class CommunityGuidelineDetailView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, generics.GenericAPIView):
    queryset = CommunityGuideline.objects.all()
    serializer_class = CommunityGuidelineSerializer

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get Community Guideline", description="Retrieve a community guideline by ID.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document)
        return success_response(data=serializer.data, message="Community guideline retrieved successfully.")

    @extend_schema(summary="Update Community Guideline (Partial)", description="Partially update an existing community guideline (Admin only).", tags=['Support'])
    def patch(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Community guideline updated successfully.")
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class ReportBugListCreateView(generics.ListCreateAPIView):
    queryset = BugReport.objects.all()
    serializer_class = BugReportSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @extend_schema(summary="View Bug Reports", description="Allows an admin to view bug reports.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Bug reports retrieved successfully.")

    @extend_schema(summary="Report a Bug", description="Allows an authenticated user to submit a bug report.", tags=['Support'])
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return success_response(data=serializer.data, message="Bug report submitted successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)
