from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from apps.common.utils import success_response, error_response
from .models import FAQ, LegalDocument, BugReport
from .serializers import FAQSerializer, LegalDocumentSerializer, BugReportSerializer

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
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="FAQ created successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class LegalDocumentListCreateView(generics.ListCreateAPIView):
    queryset = LegalDocument.objects.all()
    serializer_class = LegalDocumentSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(summary="Get All Legal Documents", description="Retrieve all legal documents.", tags=['Support'])
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Legal documents retrieved successfully.")

    @extend_schema(summary="Create Legal Document", description="Allows an admin to create a new legal document.", tags=['Support'])
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(data=serializer.data, message="Legal document created successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)

class LegalDocumentView(generics.RetrieveAPIView):
    queryset = LegalDocument.objects.all()
    serializer_class = LegalDocumentSerializer
    permission_classes = (AllowAny,)
    lookup_field = 'document_type'

    @extend_schema(summary="Get Legal Document", description="Retrieve a legal document by its type (terms, privacy, guidelines).", tags=['Support'])
    def get(self, request, *args, **kwargs):
        document_type = self.kwargs.get(self.lookup_field)
        document = get_object_or_404(LegalDocument, document_type=document_type)
        serializer = self.get_serializer(document)
        return success_response(data=serializer.data, message=f"{document_type} retrieved successfully.")

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
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return success_response(data=serializer.data, message="Bug report submitted successfully.", status=status.HTTP_201_CREATED)
        return error_response(errors=serializer.errors, message="Invalid data", status=status.HTTP_400_BAD_REQUEST)
