from rest_framework.pagination import PageNumberPagination, CursorPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

class CursorSetPagination(CursorPagination):
    page_size = 10
    ordering = '-created_at'

class ForYouCursorPagination(CursorPagination):
    page_size = 10
    ordering = ('-priority', '-created_at', '-id')
