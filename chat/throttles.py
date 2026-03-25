from rest_framework.throttling import SimpleRateThrottle


class ChatRateThrottle(SimpleRateThrottle):
    """30 requests/min per IP on the REST chat endpoint."""
    scope = 'chat'

    def get_cache_key(self, request, view):
        return self.get_ident(request)
