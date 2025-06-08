import json
from .models import APIRequestLog

class APIRequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)
        
        # Log only API requests
        if request.path.startswith('/api/'):
            # Try to get request body
            try:
                request_body = request.body.decode('utf-8')
            except:
                request_body = None
                
            # Create log entry
            APIRequestLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                endpoint=request.path,
                method=request.method,
                request_path=request.get_full_path(),
                request_body=request_body,
                response_code=response.status_code,
                ip_address=self.get_client_ip(request)
            )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
