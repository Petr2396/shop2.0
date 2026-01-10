# payments/middleware.py
class CloudflareMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Cloudflare передает реальный IP в заголовках
        if 'CF-Connecting-IP' in request.headers:
            request.META['REMOTE_ADDR'] = request.headers['CF-Connecting-IP']
        
        response = self.get_response(request)
        return response