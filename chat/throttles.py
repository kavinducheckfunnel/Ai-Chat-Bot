from rest_framework.throttling import SimpleRateThrottle


class ChatRateThrottle(SimpleRateThrottle):
    """30 requests/min per IP on the REST chat endpoint."""
    scope = 'chat'

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class SessionRateThrottle(SimpleRateThrottle):
    """10 requests/min per session_id — prevents a single bot session flooding
    the endpoint even from rotating IPs."""
    scope = 'chat_session'

    def get_cache_key(self, request, view):
        session_id = request.data.get('session_id') or request.query_params.get('session_id')
        if not session_id:
            return None  # No session_id — fall through to IP throttle only
        return f'throttle_session_{session_id}'
