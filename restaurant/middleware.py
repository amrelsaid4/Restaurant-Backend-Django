from django.contrib.sessions.models import Session
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
import re
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class CSRFExemptMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Exempt these URLs from CSRF
        self.exempt_urls = [
            re.compile(r'/api/add-rating/'),
            re.compile(r'/api/submit-rating/'),
            re.compile(r'/api/update-rating/\d+/'),
            re.compile(r'/api/login/'),
            re.compile(r'/api/admin/login/'),
            re.compile(r'/api/logout/'),
            re.compile(r'/api/stripe/.*'),
        ]

    def __call__(self, request):
        # Check if the request path should be exempt from CSRF
        for url_pattern in self.exempt_urls:
            if url_pattern.match(request.path):
                setattr(request, '_dont_enforce_csrf_checks', True)
                break
        
        response = self.get_response(request)
        return response

class SessionKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Check for session key in headers
            session_key = request.headers.get('X-Session-Key')
            
            # Make sure request.user exists (should be set by AuthenticationMiddleware)
            if not hasattr(request, 'user'):
                logger.warning("No user attribute on request")
                response = self.get_response(request)
                return response
            
            if session_key and not request.user.is_authenticated:
                try:
                    session = Session.objects.get(session_key=session_key)
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    
                    if user_id:
                        try:
                            user = User.objects.get(id=user_id)
                            
                            # Set user with authentication backend
                            user.backend = 'django.contrib.auth.backends.ModelBackend'
                            request.user = user
                            
                            # Properly restore the session
                            request.session = SessionStore(session_key=session_key)
                            request.session.load()
                            
                        except User.DoesNotExist:
                            logger.warning(f"User with id {user_id} not found")
                            pass
                except Session.DoesNotExist:
                    logger.warning(f"Session with key {session_key} not found")
                    pass

            response = self.get_response(request)
            
            # Add session key to response headers if user is authenticated
            if hasattr(request, 'user') and request.user.is_authenticated and hasattr(request, 'session'):
                if hasattr(request.session, 'session_key') and request.session.session_key:
                    response['X-Session-Key'] = request.session.session_key
            
            return response
            
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            import traceback
            traceback.print_exc()  # Print full traceback for debugging
            # If middleware fails, continue with normal flow
            response = self.get_response(request)
            return response 