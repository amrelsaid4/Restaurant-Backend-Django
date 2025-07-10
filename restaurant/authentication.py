from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework import authentication, exceptions
from .models import Customer
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class SessionAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        session_key = request.headers.get('X-Session-Key')
        if not session_key:
            return None

        try:
            session = Session.objects.get(session_key=session_key, expire_date__gte=timezone.now())
            session_data = session.get_decoded()

            # Django's default session key for user ID is '_auth_user_id'
            admin_user_id = session_data.get('_auth_user_id')
            if admin_user_id:
                try:
                    user = User.objects.get(pk=admin_user_id)
                    # For admin users, the user object itself is returned.
                    # The IsRestaurantAdmin permission class will check the profile.
                    return (user, None)
                except User.DoesNotExist:
                    logger.warning(f"Admin user with ID {admin_user_id} not found for session {session_key}")
                    raise exceptions.AuthenticationFailed('Invalid admin session: User not found.')

            customer_uid = session_data.get('uid')
            if customer_uid:
                try:
                    customer = Customer.objects.get(pk=customer_uid)
                    # For customers, the customer object is returned.
                    return (customer, None)
                except Customer.DoesNotExist:
                    logger.warning(f"Customer with ID {customer_uid} not found for session {session_key}")
                    raise exceptions.AuthenticationFailed('Invalid customer session: Customer not found.')
            
            # If neither an admin nor a customer user ID is found in the session.
            logger.warning(f"Session {session_key[:6]}... is valid but contains no user identifier ('_auth_user_id' or 'uid').")
            return None

        except Session.DoesNotExist:
            logger.info(f"Session key {session_key[:6]}... not found in database or expired. Request will be treated as anonymous.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during authentication for session key {session_key[:6]}...: {e}", exc_info=True)
            raise exceptions.AuthenticationFailed('An unexpected server error occurred during authentication.')


class CustomerAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        session_key = request.headers.get('X-Session-Key')
        if not session_key:
            return None

        try:
            session = Session.objects.get(session_key=session_key, expire_date__gte=timezone.now())
            uid = session.get_decoded().get('uid')
            if not uid:
                return None
            
            customer = Customer.objects.get(pk=uid)
            return (customer, None)
        except (Session.DoesNotExist, Customer.DoesNotExist):
            return None 