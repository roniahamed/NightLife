import time
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog

class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, 'start_time') and request.path.startswith('/api/'):
            execution_time = (time.time() - request.start_time) * 1000
            
            # Extract IP Address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            user = request.user if request.user.is_authenticated else None
            
            # Fire and forget Audit log creation (synchronous for now, could be pushed to Celery later)
            AuditLog.objects.create(
                user=user,
                ip_address=ip,
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                execution_time_ms=execution_time
            )
            
        return response
