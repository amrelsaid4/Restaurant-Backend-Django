from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from rest_framework import authentication, exceptions
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class SessionKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class to authenticate users using a session key
    passed in the 'X-Session-Key' header.
    """
    def authenticate(self, request):
        session_key = request.headers.get('X-Session-Key')

        if not session_key:
            return None

        try:
            session = Session.objects.get(session_key=session_key)
            session_data = session.get_decoded()
            user_id = session_data.get('_auth_user_id')

            if not user_id:
                logger.warning(f"No user_id found in session data for key {session_key[:6]}...")
                return None

            user = User.objects.get(id=user_id)
            
        except Session.DoesNotExist:
            # This is not necessarily an error, just an invalid session.
            # Raising an exception would cause a 403 error for any invalid key,
            # which might not be desirable. Returning None lets other auth methods try.
            logger.info(f"Session with key {session_key[:6]}... is invalid or expired.")
            return None
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} from session does not exist.")
            # This is a server error, but from a client perspective, it's an auth failure.
            raise exceptions.AuthenticationFailed('User for session not found.')
        except Exception as e:
            logger.error(f"An unexpected error occurred during session authentication: {e}")
            raise exceptions.AuthenticationFailed('Session authentication failed due to a server error.')

        # If we get here, authentication was successful.
        # Set the user on the request for other parts of Django/DRF to use.
        request.user = user
        return (user, None)

    def authenticate_header(self, request):
        return 'Session' 