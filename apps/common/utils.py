from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

def success_response(data=None, message="Success", status=200):
    """
    Standardized success response wrapper.
    """
    return Response({
        "status": "success",
        "message": message,
        "data": data
    }, status=status)

def error_response(errors=None, message="Error", status=400):
    """
    Standardized error response wrapper.
    """
    return Response({
        "status": "error",
        "message": message,
        "errors": errors
    }, status=status)

class CacheMixin:
    """
    Mixin to cache list and retrieve views.
    By default caches for 15 minutes.
    """
    cache_timeout = 60 * 15

    @method_decorator(cache_page(cache_timeout))
    @method_decorator(vary_on_headers('Authorization', 'Accept', 'Cookie'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
