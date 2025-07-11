from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.models import User
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from django.conf import settings
import stripe
import json
import logging
import time

from .utils import account_activation_token_generator, send_verification_email
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.shortcuts import redirect

from .models import (
    Category, Dish, Customer, Order, OrderItem, DishRating, 
    Restaurant, AdminProfile, Notification, OrderAnalytics, ContactMessage
)
from .serializers import (
    CategorySerializer, DishSerializer, CustomerSerializer,
    OrderSerializer, OrderCreateSerializer, DishRatingSerializer,
    RestaurantSerializer, UserSerializer, NotificationSerializer,
    OrderAnalyticsSerializer, EnhancedOrderCreateSerializer, AdminDishSerializer
)
from .filters import DishFilter, CategoryFilter, OrderFilter, DishRatingFilter
from django.db.models import Count, Avg, Sum
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import logout
from django.shortcuts import redirect
from .serializers import ContactMessageSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Stripe from settings
try:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    logger.info("Stripe initialized successfully")
except Exception as e:
    logger.error(f"Error setting Stripe key: {e}")
    stripe.api_key = None

# Custom permission class for admin email check
class IsRestaurantAdmin(permissions.BasePermission):
    """
    Custom permission to only allow users with admin email to access admin views.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has admin profile with valid admin email
        return AdminProfile.is_admin_email(request.user.email) or request.user.is_superuser

# ========================================
# 🎯 CUSTOMER VIEWS (Public & Customer)
# ========================================

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True).prefetch_related('dish_set')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filterset_class = CategoryFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class DishViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Dish.objects
        .filter(is_available=True)
        .select_related('category')
        .prefetch_related('dishrating_set')
    )
    serializer_class = DishSerializer
    permission_classes = [AllowAny]
    filterset_class = DishFilter
    search_fields = ['name', 'description', 'ingredients']
    ordering_fields = ['name', 'price', 'created_at', 'average_rating']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """الأطباق الشعبية"""
        popular_dishes = get_popular_dishes(limit=10)
        return Response(popular_dishes)
    
    @action(detail=False, methods=['get'])
    def most_ordered(self, request):
        """Most ordered dishes based on order items"""
        from django.db.models import Sum, Count
        
        # Get dishes ordered by total quantity
        dishes = Dish.objects.filter(is_available=True).annotate(
            total_ordered=Sum('orderitem__quantity'),
            order_count=Count('orderitem')
        ).filter(
            total_ordered__isnull=False
        ).order_by('-total_ordered')[:10]
        
        serializer = self.get_serializer(dishes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """الأطباق ذات المخزون المنخفض"""
        if not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=403)
        
        low_stock_dishes = Dish.objects.filter(
            stock_quantity__lte=models.F('low_stock_threshold')
        ).select_related('category')
        serializer = self.get_serializer(low_stock_dishes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        dish = self.get_object()
        ratings = DishRating.objects.filter(dish=dish)
        serializer = DishRatingSerializer(ratings, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def reviews(self, request, pk=None):
        """Handle dish reviews - same as ratings but for frontend compatibility"""
        dish = self.get_object()
        
        if request.method == 'GET':
            ratings = DishRating.objects.filter(dish=dish).order_by('-created_at')
            serializer = DishRatingSerializer(ratings, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=401)
            
            # Get or create customer for the user
            try:
                customer = request.user.customer
            except Customer.DoesNotExist:
                customer = Customer.objects.create(
                    user=request.user,
                    phone='',
                    address=''
                )
            
            # Create the review
            data = request.data.copy()
            data['dish'] = dish.id
            data['customer'] = customer.id
            
            serializer = DishRatingSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=201)
            else:
                return Response(serializer.errors, status=400)

class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    serializer_class = RestaurantSerializer
    permission_classes = [AllowAny]

# ViewSets جديدة للميزات المتقدمة
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """عرض إشعارات المستخدم فقط"""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """تحديد الإشعار كمقروء"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """تحديد جميع الإشعارات كمقروءة"""
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all notifications marked as read'})

class OrderAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderAnalyticsSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return OrderAnalytics.objects.all().order_by('-date')
    
    @action(detail=False, methods=['get'])
    def weekly_stats(self, request):
        """إحصائيات الأسبوع"""
        from .utils import get_weekly_stats
        stats = get_weekly_stats()
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def monthly_stats(self, request):
        """إحصائيات الشهر"""
        from .utils import get_monthly_stats
        stats = get_monthly_stats()
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def calculate_daily(self, request):
        """حساب الإحصائيات اليومية"""
        date = request.data.get('date')
        analytics = calculate_daily_analytics(date)
        serializer = self.get_serializer(analytics)
        return Response(serializer.data)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]  # Changed to handle session authentication manually
    
    def get_queryset(self):
        # Try to get authenticated user
        current_user = self.request.user
        
        # If not authenticated, try session-based authentication
        if not current_user or current_user.is_anonymous:
            session_key = self.request.headers.get('X-Session-Key')
            if session_key:
                try:
                    from django.contrib.sessions.models import Session
                    session = Session.objects.get(session_key=session_key)
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        current_user = User.objects.get(id=user_id)
                        logger.info(f"Found user via session: {current_user.username}")
                except Exception as e:
                    logger.warning(f"Session authentication failed: {e}")
                    return Order.objects.none()
        
        # If still no user, return empty
        if not current_user or current_user.is_anonymous:
            logger.warning("No authenticated user found for orders")
            return Order.objects.none()
            
        # Get customer and their orders
        try:
            customer = current_user.customer
            orders = Order.objects.filter(customer=customer).order_by('-order_date')
            logger.info(f"Found {orders.count()} orders for user {current_user.username}")
            return orders
        except Customer.DoesNotExist:
            logger.warning(f"No customer found for user {current_user.username}")
            # Try to create customer profile if missing
            try:
                Customer.objects.create(
                    user=current_user,
                    phone='',
                    address=''
                )
                logger.info(f"Created customer profile for user {current_user.username}")
                # Return orders after creating customer
                return Order.objects.filter(customer__user=current_user).order_by('-order_date')
            except Exception as e:
                logger.error(f"Failed to create customer for user {current_user.username}: {e}")
                return Order.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        customer, created = Customer.objects.get_or_create(
            user=self.request.user,
            defaults={
                'phone': '',
                'address': serializer.validated_data.get('delivery_address', '')
            }
        )
        serializer.save(customer=customer)

@method_decorator(csrf_exempt, name='dispatch')
class DishRatingViewSet(viewsets.ModelViewSet):
    serializer_class = DishRatingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request.user, 'customer'):
            return DishRating.objects.filter(customer=self.request.user.customer)
        return DishRating.objects.none()
    
    def perform_create(self, serializer):
        customer, created = Customer.objects.get_or_create(
            user=self.request.user,
            defaults={'phone': '', 'address': ''}
        )
        serializer.save(customer=customer)

# ========================================
# 🛡️ ADMIN VIEWS (Staff Only)
# ========================================

class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsRestaurantAdmin]

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

class AdminDishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    permission_classes = [IsRestaurantAdmin]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_class(self):
        """
        Use AdminDishSerializer for write actions (create, update)
        and the default DishSerializer for read actions (list, retrieve).
        """
        if self.action in ['create', 'update', 'partial_update']:
            return AdminDishSerializer
        return DishSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info(f"Admin creating dish. Content-Type: {request.content_type}")
        logger.info(f"Admin creating dish. POST data: {request.POST}")
        logger.info(f"Admin creating dish. FILES data: {request.FILES}")
        logger.info(f"Admin creating dish. Raw request.data: {request.data}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Admin dish creation failed. Errors: {serializer.errors}")
                return Response(serializer.errors, status=400)
            
            # Create the dish
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            
            logger.info(f"✅ Dish created successfully: {serializer.data}")
            return Response(serializer.data, status=201, headers=headers)
            
        except Exception as e:
            logger.error(f"❌ Error creating dish: {str(e)}")
            return Response({'error': 'Failed to create dish'}, status=500)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Override update to add debugging and atomic transactions for PATCH requests"""
        logger.info(f"📝 AdminDishViewSet PATCH request data: {request.data}")
        logger.info(f"📝 Content-Type: {request.content_type}")
        logger.info(f"📝 Files: {request.FILES}")
        
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            # Log current instance data
            logger.info(f"📝 Current dish: {instance.name} (ID: {instance.id})")
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if not serializer.is_valid():
                logger.error(f"❌ Validation errors: {serializer.errors}")
                return Response(serializer.errors, status=400)
            
            # Update the dish
            self.perform_update(serializer)
            
            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}

            logger.info(f"✅ Dish updated successfully: {serializer.data}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"❌ Error updating dish: {str(e)}")
            return Response({'error': 'Failed to update dish'}, status=500)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dish statistics for admin dashboard"""
        total_dishes = Dish.objects.count()
        available_dishes = Dish.objects.filter(is_available=True).count()
        vegetarian_dishes = Dish.objects.filter(is_vegetarian=True).count()
        spicy_dishes = Dish.objects.filter(is_spicy=True).count()
        
        return Response({
            'total_dishes': total_dishes,
            'available_dishes': available_dishes,
            'vegetarian_dishes': vegetarian_dishes,
            'spicy_dishes': spicy_dishes
        })
    
    @transaction.atomic
    @action(detail=True, methods=['patch'])
    def set_availability(self, request, pk=None):
        """Toggle dish availability with atomic transaction"""
        try:
            dish = self.get_object()
            is_available = request.data.get('is_available', dish.is_available)
            
            dish.is_available = is_available
            dish.save(update_fields=['is_available'])
            
            logger.info(f"✅ Dish availability updated: {dish.name} -> {dish.is_available}")
            return Response({
                'message': 'Dish availability updated successfully',
                'is_available': dish.is_available
            })
        except Exception as e:
            logger.error(f"❌ Error updating dish availability: {str(e)}")
            return Response({'error': 'Failed to update availability'}, status=500)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add atomic transaction and logging"""
        try:
            instance = self.get_object()
            dish_name = instance.name
            dish_id = instance.id
            
            # Delete the dish
            self.perform_destroy(instance)
            
            logger.info(f"✅ Dish deleted successfully: {dish_name} (ID: {dish_id})")
            return Response({'message': f'Dish "{dish_name}" deleted successfully'}, status=204)
            
        except Exception as e:
            logger.error(f"❌ Error deleting dish: {str(e)}")
            return Response({'error': 'Failed to delete dish'}, status=500)

class AdminOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsRestaurantAdmin]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get order statistics for admin dashboard"""
        from django.db.models import Count, Sum
        
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        total_revenue = Order.objects.filter(payment_status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Orders by status
        orders_by_status = Order.objects.values('status').annotate(
            count=Count('id')
        )
        
        return Response({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'delivered_orders': delivered_orders,
            'total_revenue': float(total_revenue),
            'orders_by_status': list(orders_by_status)
        })
    
    @csrf_exempt
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update order status"""
        # Force CSRF exemption
        setattr(request, '_dont_enforce_csrf_checks', True)
        
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.status = new_status
            order.save()
            return Response({'message': 'Order status updated successfully'})
        
        return Response({'error': 'Invalid status'}, status=400)

class AdminCustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsRestaurantAdmin]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get customer statistics"""
        total_customers = Customer.objects.count()
        customers_with_orders = Customer.objects.filter(order__isnull=False).distinct().count()
        
        return Response({
            'total_customers': total_customers,
            'customers_with_orders': customers_with_orders
        })

class AdminRestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsRestaurantAdmin]


class ContactMessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for admins to view contact messages.
    Provides `list` and `retrieve` actions.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [IsRestaurantAdmin]


# ========================================
# 🌟 PUBLIC API FUNCTIONS
# ========================================

@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_info(request):
    """Get basic restaurant information"""
    restaurant = Restaurant.objects.filter(is_active=True).first()
    if restaurant:
        serializer = RestaurantSerializer(restaurant)
        return Response(serializer.data)
    return Response({'message': 'Restaurant information not available'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def menu_overview(request):
    """Get menu overview with categories and featured dishes"""
    categories = Category.objects.filter(is_active=True)
    featured_dishes = Dish.objects.filter(is_available=True)[:6]
    
    return Response({
        'categories': CategorySerializer(categories, many=True).data,
        'featured_dishes': DishSerializer(featured_dishes, many=True).data
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user and customer.
    The user will be inactive until their email is verified.
    """
    data = request.data
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    # Phone number is now optional
    phone_number = data.get('phone_number', '') 

    # Basic validation
    if not all([email, username, password]):
        return Response(
            {'error': 'Email, username, and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check for existing user
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    # Create new user
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False  # Deactivate until email is verified
        )
        logger.info(f"User '{username}' created but inactive.")

        # Create customer profile
        customer = Customer.objects.create(
            user=user,
            phone=phone_number,
            address=data.get('address', '')
        )
        logger.info(f"Customer profile created for '{username}'.")

        # Send verification email
        email_sent = send_verification_email(user, request._request)
        if not email_sent:
            # We don't roll back, but we notify the frontend.
            # The user can request a new verification email.
            logger.warning(f"Failed to send verification email for '{username}'.")
            # The response still indicates success, but with a warning.
            # The frontend should handle this.
            user_data = UserSerializer(user).data
            user_data['warning'] = 'User created, but failed to send verification email.'
            return Response(user_data, status=status.HTTP_201_CREATED)

        # Return user data
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error during user registration for '{username}': {e}", exc_info=True)
        # Clean up user if something else went wrong during profile creation
        if 'user' in locals() and not Customer.objects.filter(user=user).exists():
            user.delete()
        return Response(
            {'error': 'An unexpected error occurred during registration.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_contact_form(request):
    """
    Handles submission of the contact form.
    Creates a new ContactMessage instance.
    """
    logger.info(f"Contact form submission received. Data: {request.data}")
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        # Optionally, send an email notification to the admin here
        return Response(
            {'message': 'Your message has been received. Thank you!'},
            status=status.HTTP_201_CREATED
        )
    logger.error(f"Contact form validation failed. Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, uidb64, token):
    """
    Verify email address from the link sent to the user.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        try:
            customer = user.customer
            customer.is_email_verified = True
            customer.save()
        except Customer.DoesNotExist:
            # This should not happen if registration is atomic
            logger.error(f"Critical: Customer profile not found for user {user.username} during email verification.")
            pass

        login(request, user)
        # Redirect to a success page on the frontend
        # The frontend should handle displaying a success message.
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        return redirect(f"{frontend_url}/login?verified=true")
    else:
        # Redirect to an invalid link page on the frontend
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        return redirect(f"{frontend_url}/invalid-verification-link")


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """
    Resends the verification email to a user who has not yet activated their account.
    """
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal that the user does not exist
        return Response({'message': 'If an account with that email exists, a new verification link has been sent.'}, status=status.HTTP_200_OK)

    if user.is_active:
        return Response({'message': 'This account has already been activated.'}, status=status.HTTP_400_BAD_REQUEST)

    # Resend the verification email
    email_sent = send_verification_email(user, request._request)
    if email_sent:
        logger.info(f"Verification email resent to {user.email}")
        return Response({'message': 'A new verification link has been sent to your email.'}, status=status.HTTP_200_OK)
    else:
        logger.error(f"Failed to resend verification email to {user.email}")
        return Response({'error': 'Failed to send verification email. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Fetches the extended user profile including stats and additional info.
    """
    user = request.user
    try:
        customer = user.customer
    except Customer.DoesNotExist:
        return Response({'error': 'Customer profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Get user stats
    total_orders = Order.objects.filter(customer=customer).count()
    avg_rating = DishRating.objects.filter(customer=customer).aggregate(Avg('rating'))['rating__avg']
    
    # Recent orders
    recent_orders = Order.objects.filter(customer=customer).order_by('-order_date')[:5]
    
    # Favorite dishes (most ordered)
    favorite_dishes = OrderItem.objects.filter(order__customer=customer)\
        .values('dish__name', 'dish__id')\
        .annotate(total_ordered=Sum('quantity'))\
        .order_by('-total_ordered')[:3]
    
    # VIP status logic (example: > 10 orders)
    is_vip = total_orders > 10

    serializer = UserSerializer(user)
    profile_data = serializer.data
    profile_data.update({
        'username': user.username,  # Add username
        'phone': customer.phone,
        'address': customer.address,
        'is_email_verified': customer.is_email_verified,
        'stats': {
            'total_orders': total_orders,
            'avg_rating': round(avg_rating, 1) if avg_rating else 0,
            'is_vip': is_vip,
        },
        'recent_orders': [
            {
                'id': order.id,
                'date': order.order_date,
                'status': order.status,
                'total': order.total_amount
            } for order in recent_orders
        ],
        'favorite_dishes': list(favorite_dishes),
        'preferences': {
            'notifications_enabled': True,  # Default preference
            'email_notifications': True,
        },
        'security': {
            'last_login': user.last_login,
            'date_joined': user.date_joined,
            'password_last_changed': None,  # We can implement this later
        }
    })
    
    return Response(profile_data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """Update user profile (name, phone, address)"""
    user = request.user
    try:
        customer = user.customer
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=404)

    # Update User model
    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.save()

    # Update Customer model
    customer.phone = request.data.get('phone', customer.phone)
    customer.address = request.data.get('address', customer.address)
    customer.save()

    # Return updated data
    user_serializer = UserSerializer(user)
    customer_serializer = CustomerSerializer(customer)
    
    response_data = user_serializer.data
    response_data.update(customer_serializer.data)

    return Response(response_data)

# ========================================
# 🎛️ ADMIN DASHBOARD API
# ========================================

@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow any for testing
def admin_dashboard_stats(request):
    """Get comprehensive admin dashboard statistics - optimized version"""
    from django.db.models import Count, Sum, Avg, Case, When, Q
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Optimize multiple queries into single aggregations
    order_stats = Order.objects.aggregate(
        total_orders=Count('id'),
        today_orders=Count('id', filter=Q(order_date__date=today)),
        yesterday_orders=Count('id', filter=Q(order_date__date=yesterday)),
        recent_orders=Count('id', filter=Q(order_date__gte=week_ago)),
        pending_orders=Count('id', filter=Q(status='pending')),
        delivered_orders=Count('id', filter=Q(status='delivered')),
        total_revenue=Sum('total_amount', filter=Q(payment_status='paid')),
        today_revenue=Sum('total_amount', filter=Q(order_date__date=today, payment_status='paid')),
        yesterday_revenue=Sum('total_amount', filter=Q(order_date__date=yesterday, payment_status='paid')),
        recent_revenue=Sum('total_amount', filter=Q(order_date__gte=week_ago, payment_status='paid')),
        avg_order_value=Avg('total_amount', filter=Q(payment_status='paid'))
    )
    
    # Basic counts in single queries
    total_customers = Customer.objects.count()
    total_dishes = Dish.objects.count()
    total_categories = Category.objects.count()
    active_customers = Customer.objects.filter(user__last_login__gte=week_ago).count()
    
    # Order status breakdown
    order_statuses = Order.objects.values('status').annotate(count=Count('id'))
    
    # Top dishes by orders
    top_dishes = OrderItem.objects.select_related('dish').values('dish__name').annotate(
        total_ordered=Sum('quantity')
    ).order_by('-total_ordered')[:5]
    
    # Average rating
    avg_rating = DishRating.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Calculate percentage changes
    orders_change = ((order_stats['today_orders'] - order_stats['yesterday_orders']) / max(order_stats['yesterday_orders'], 1)) * 100 if order_stats['yesterday_orders'] else 0
    revenue_change = ((order_stats['today_revenue'] or 0) - (order_stats['yesterday_revenue'] or 0)) / max(order_stats['yesterday_revenue'] or 1, 1) * 100 if order_stats['yesterday_revenue'] else 0
    
    return Response({
        'overview': {
            'total_orders': order_stats['total_orders'],
            'total_customers': total_customers,
            'total_dishes': total_dishes,
            'total_categories': total_categories,
            'total_revenue': float(order_stats['total_revenue'] or 0),
            'average_rating': round(float(avg_rating), 2)
        },
        'today_stats': {
            'today_orders': order_stats['today_orders'],
            'today_revenue': float(order_stats['today_revenue'] or 0),
            'yesterday_orders': order_stats['yesterday_orders'],
            'yesterday_revenue': float(order_stats['yesterday_revenue'] or 0),
            'orders_change': round(float(orders_change), 1),
            'revenue_change': round(float(revenue_change), 1)
        },
        'recent_stats': {
            'recent_orders': order_stats['recent_orders'],
            'recent_revenue': float(order_stats['recent_revenue'] or 0),
            'active_customers': active_customers,
            'pending_orders': order_stats['pending_orders']
        },
        'performance': {
            'delivered_orders': order_stats['delivered_orders'],
            'average_order_value': round(float(order_stats['avg_order_value'] or 0), 2),
            'completion_rate': round((order_stats['delivered_orders'] / max(order_stats['total_orders'], 1)) * 100, 1)
        },
        'order_statuses': list(order_statuses),
        'top_dishes': list(top_dishes)
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def homepage_stats(request):
    """Get homepage statistics for main landing page"""
    from django.db.models import Count, Sum, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    # Total customers count
    total_customers = Customer.objects.count()
    
    # Today's dishes served (total order items for today)
    today = timezone.now().date()
    dishes_served_today = OrderItem.objects.filter(
        order__order_date__date=today,
        order__status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Total menu items available
    menu_items = Dish.objects.filter(is_available=True).count()
    
    # Average rating across all dishes
    avg_rating = DishRating.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    return Response({
        'total_customers': total_customers,
        'dishes_served_today': dishes_served_today,
        'menu_items': menu_items,
        'average_rating': round(float(avg_rating), 1)
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Get CSRF token for frontend and ensure cookie is set"""
    token = get_token(request)
    response = Response({'csrf_token': token})
    
    # Explicitly set CSRF cookie
    response.set_cookie(
        'csrftoken',
        token,
        max_age=None,
        expires=None,
        path='/',
        domain=None,
        secure=False,
        httponly=False,
        samesite='Lax'
    )
    
    return response

@csrf_exempt
def customer_login(request):
    """Customer login endpoint"""
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        identity = data.get('identity')
        password = data.get('password')
        
        logger.info(f"🔐 Customer login attempt: {identity}")
        
        if not identity or not password:
            return JsonResponse({'error': 'Identity and password are required'}, status=400)
        
        # Try to find user by username or email
        user = None
        if '@' in identity:
            try:
                user = User.objects.get(email=identity)
                logger.info(f"📧 Found user by email: {user.username}")
            except User.DoesNotExist:
                logger.warning(f"❌ No user found with email: {identity}")
        else:
            try:
                user = User.objects.get(username=identity)
                logger.info(f"👤 Found user by username: {user.username}")
            except User.DoesNotExist:
                logger.warning(f"❌ No user found with username: {identity}")
        
        if not user:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
        
        # Check password
        if not user.check_password(password):
            logger.warning(f"❌ Invalid password for user: {user.username}")
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
        
        # Ensure user has customer profile (allow admin users if they have customer profile)
        if not hasattr(user, 'customer'):
            logger.warning(f"❌ User has no customer profile: {user.username}")
            return JsonResponse({'error': 'User is not a customer'}, status=403)
        
        # Log the user in
        login(request, user)
        
        # Session is automatically created by login(), no need to force it
        request.session['user_id'] = user.id
        request.session['is_customer'] = True
        request.session['customer_email'] = user.email
        request.session.save()
        
        session_key = request.session.session_key
        logger.info(f"✅ User logged in successfully: {user.username}, session: {session_key}")
        logger.info(f"🔍 Session data: {dict(request.session)}")
        
        response_data = {
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_admin': user.is_staff or user.is_superuser,
                'is_customer': hasattr(user, 'customer')
            },
            'session_key': session_key
        }
        
        response = JsonResponse(response_data)
        response['Access-Control-Allow-Credentials'] = 'true'
        
        # Set session cookie explicitly
        response.set_cookie(
            'sessionid',
            session_key,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False,  # Development mode
            samesite='Lax',
            path='/'
        )
        
        return response
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({'error': 'Login failed'}, status=500)

@csrf_exempt
def admin_login(request):
    """Admin login endpoint"""
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        logger.info(f"🔐 Admin login attempt: {email}")
        
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)
        
        # Check if email is admin
        if not AdminProfile.is_admin_email(email):
            logger.warning(f"❌ Not an admin email: {email}")
            return JsonResponse({'error': 'Unauthorized: Not an admin email'}, status=403)
        
        # Find user
        try:
            user = User.objects.get(email=email)
            logger.info(f"📧 Found admin user: {user.username}")
        except User.DoesNotExist:
            logger.warning(f"❌ No user found with email: {email}")
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
        
        # Check password
        if not user.check_password(password):
            logger.warning(f"❌ Invalid password for admin: {user.username}")
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
        
        # Log the user in
        login(request, user)
        
        # Check if admin also has customer profile
        has_customer = hasattr(user, 'customer')
        logger.info(f"🔍 Admin user has customer profile: {has_customer}")
        
        # Session is automatically created by login(), no need to force it
        request.session['user_id'] = user.id
        request.session['is_admin'] = True
        request.session['is_customer'] = has_customer  # Add customer flag for dual-role users
        request.session['admin_email'] = email
        request.session.save()
        
        session_key = request.session.session_key
        logger.info(f"✅ Admin logged in successfully: {user.username}, session: {session_key}")
        logger.info(f"🔍 Session data: {dict(request.session)}")
        
        # Get admin profile
        admin_profile = AdminProfile.objects.get(admin_email=email)
        
        response_data = {
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_admin': True,
                'is_customer': has_customer,
                'is_super_admin': admin_profile.is_super_admin
            },
            'session_key': session_key
        }
        
        response = JsonResponse(response_data)
        response['Access-Control-Allow-Credentials'] = 'true'
        
        # Set session cookie explicitly
        response.set_cookie(
            'sessionid',
            session_key,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False,  # Development mode
            samesite='Lax',
            path='/'
        )
        
        return response
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        return JsonResponse({'error': 'Admin login failed'}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_user_type(request):
    """Check if current user is admin or customer"""
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 Checking user type for request")
    logger.info(f"🔍 Session key: {request.session.session_key}")
    logger.info(f"🔍 Session data: {dict(request.session)}")
    logger.info(f"🔍 User authenticated: {request.user.is_authenticated}")
    logger.info(f"🔍 User: {request.user}")
    
    # Check for X-Session-Key header first
    session_key_header = request.headers.get('X-Session-Key')
    if session_key_header:
        logger.info(f"🔑 Found X-Session-Key header: {session_key_header[:10]}...")
        
        try:
            from django.contrib.sessions.models import Session
            session = Session.objects.get(session_key=session_key_header)
            session_data = session.get_decoded()
            logger.info(f"🔍 Session data from header: {session_data}")
            
            user_id = session_data.get('user_id')
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    logger.info(f"✅ Found user from X-Session-Key: {user.username}")
                    
                    # Get admin/customer status from session
                    is_admin = session_data.get('is_admin', False)
                    is_customer = session_data.get('is_customer', False)
                    
                    response_data = {
                        'user_id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_admin': is_admin,
                        'is_customer': is_customer,
                        'is_authenticated': True
                    }
                    
                    if is_admin:
                        try:
                            admin_profile = AdminProfile.objects.get(admin_email=user.email)
                            response_data['is_super_admin'] = admin_profile.is_super_admin
                            logger.info(f"✅ Super admin status: {admin_profile.is_super_admin}")
                        except AdminProfile.DoesNotExist:
                            logger.warning(f"⚠️ AdminProfile not found for {user.email}")
                    
                    logger.info(f"✅ Final response data from X-Session-Key: {response_data}")
                    return Response(response_data)
                    
                except User.DoesNotExist:
                    logger.warning(f"❌ User not found for ID from session: {user_id}")
        except Exception as e:
            logger.error(f"❌ Error reading X-Session-Key: {e}")
    
    # Fallback to Django session middleware
    user = request.user
    if not user.is_authenticated:
        # Try to get user from current session
        user_id = request.session.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                logger.info(f"🔍 Found user from Django session: {user.username}")
            except User.DoesNotExist:
                logger.warning(f"❌ User not found in Django session: {user_id}")
                user = None
    
    if not user or not user.is_authenticated:
        logger.info("❌ User not authenticated")
        return Response({
            'user_id': None,
            'username': None,
            'email': None,
            'first_name': None,
            'last_name': None,
            'is_admin': False,
            'is_customer': False,
            'is_authenticated': False
        })
    
    is_admin = False
    
    # Check if admin from session first
    if request.session.get('is_admin'):
        is_admin = True
        logger.info(f"✅ Admin status from Django session: {is_admin}")
    else:
        # Fallback to email check
        try:
            is_admin = AdminProfile.is_admin_email(user.email)
            logger.info(f"✅ Admin check result for {user.email}: {is_admin}")
        except Exception as e:
            logger.warning(f"⚠️ Admin check failed: {e}")
    
    # Check customer status
    has_customer = False
    if request.session.get('is_customer'):
        has_customer = True
        logger.info(f"✅ Customer status from Django session: {has_customer}")
    else:
        # Fallback to model check
        has_customer = hasattr(user, 'customer')
        logger.info(f"✅ Customer check result for {user.username}: {has_customer}")
    
    response_data = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_admin': is_admin,
        'is_customer': has_customer,
        'is_authenticated': True
    }
    
    if is_admin:
        try:
            admin_profile = AdminProfile.objects.get(admin_email=user.email)
            response_data['is_super_admin'] = admin_profile.is_super_admin
            logger.info(f"✅ Super admin status: {admin_profile.is_super_admin}")
        except AdminProfile.DoesNotExist:
            logger.warning(f"⚠️ AdminProfile not found for {user.email}")
    
    logger.info(f"✅ Final response data from Django session: {response_data}")
    return Response(response_data)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def user_logout(request):
    """Logout function for all users"""
    # Force CSRF exemption
    setattr(request, '_dont_enforce_csrf_checks', True)
    
    logout(request)
    return Response({'message': 'Logout successful'})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def submit_rating_simple(request):
    """Simple rating submission without CSRF checks"""
    try:
        # Manual authentication check and user finding
        current_user = request.user
        
        # If user not authenticated but we have session info, try to find the user
        if not current_user.is_authenticated or current_user.is_anonymous:
            session_key = request.headers.get('X-Session-Key')
            if session_key:
                try:
                    from django.contrib.sessions.models import Session
                    session = Session.objects.get(session_key=session_key)
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        current_user = User.objects.get(id=user_id)
                except Exception as e:
                    logger.warning(f"Session user error: {e}")
        
        if not current_user or current_user.is_anonymous:
            return Response({'error': 'Authentication required'}, status=401)
        
        data = request.data
        
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            user=current_user,
            defaults={'phone': '', 'address': ''}
        )
        
        # Create rating
        rating = DishRating.objects.create(
            customer=customer,
            dish_id=data['dish_id'],
            rating=data['rating'],
            comment=data.get('comment', '')
        )
        
        serializer = DishRatingSerializer(rating)
        return Response(serializer.data, status=201)
        
    except Exception as e:
        logger.error(f"Error in submit_rating_simple: {e}")
        return Response({'error': str(e)}, status=400)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def add_rating(request):
    """Simple rating add function without any middleware issues"""
    try:
        data = request.data
        dish_id = data.get('dish_id')
        rating_value = data.get('rating')
        comment = data.get('comment', '')
        
        # Find user by session
        session_key = request.headers.get('X-Session-Key')
        current_user = None
        
        if session_key:
            try:
                from django.contrib.sessions.models import Session
                session = Session.objects.get(session_key=session_key)
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                if user_id:
                    current_user = User.objects.get(id=user_id)
            except Exception as e:
                logger.warning(f"Error finding user: {e}")
        
        if not current_user:
            return Response({'error': 'User not found'}, status=401)
        
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            user=current_user,
            defaults={'phone': '', 'address': ''}
        )
        
        # Always create new rating (allow multiple ratings from same user)
        rating = DishRating.objects.create(
            customer=customer,
            dish_id=dish_id,
            rating=rating_value,
            comment=comment
        )
        
        return Response({
            'success': True,
            'rating_id': rating.id,
            'message': 'Rating submitted successfully'
        }, status=201)
        
    except Exception as e:
        logger.error(f"Error in add_rating: {e}")
        return Response({'error': str(e)}, status=400)

@csrf_exempt
@api_view(['PUT'])
@permission_classes([AllowAny])
def update_rating(request, rating_id):
    """Update existing rating"""
    try:
        data = request.data
        rating_value = data.get('rating')
        comment = data.get('comment', '')
        
        # Find user by session
        session_key = request.headers.get('X-Session-Key')
        current_user = None
        
        if session_key:
            try:
                from django.contrib.sessions.models import Session
                session = Session.objects.get(session_key=session_key)
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                if user_id:
                    current_user = User.objects.get(id=user_id)
            except Exception as e:
                logger.warning(f"Error finding user: {e}")
        
        if not current_user:
            return Response({'error': 'User not found'}, status=401)
        
        # Get customer
        try:
            customer = Customer.objects.get(user=current_user)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=404)
        
        # Find and update rating
        try:
            rating = DishRating.objects.get(id=rating_id, customer=customer)
            rating.rating = rating_value
            rating.comment = comment
            rating.save()
            
            return Response({
                'success': True,
                'rating_id': rating.id,
                'message': 'Rating updated successfully'
            }, status=200)
            
        except DishRating.DoesNotExist:
            return Response({'error': 'Rating not found or not owned by user'}, status=404)
        
    except Exception as e:
        logger.error(f"Error in update_rating: {e}")
        return Response({'error': str(e)}, status=400)

# ========================================
# 💳 STRIPE PAYMENT VIEWS
# ========================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    """Create Stripe Checkout Session for complete payment flow"""
    # Force CSRF exemption
    setattr(request, '_dont_enforce_csrf_checks', True)
    
    try:
        logger.info(f"Checkout session request received from user: {request.user}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        data = request.data
        items = data.get('items', [])
        delivery_address = data.get('delivery_address', '')
        special_instructions = data.get('special_instructions', '')
        
        logger.info(f"Checkout data: items={len(items)}, address={delivery_address}")
        
        if not items:
            return Response({'error': 'No items provided'}, status=400)
        
        # Get authenticated user
        current_user = request.user
        logger.info(f"Initial user: {current_user}, authenticated: {current_user.is_authenticated}")
        
        # If user is not authenticated, check cookies
        if not current_user.is_authenticated:
            sessionid = request.COOKIES.get('sessionid')
            logger.info(f"Checking sessionid cookie: {sessionid}")
            if sessionid:
                try:
                    from django.contrib.sessions.models import Session
                    session = Session.objects.get(session_key=sessionid)
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        current_user = User.objects.get(id=user_id)
                        logger.info(f"Found user via sessionid cookie: {current_user}")
                except Exception as e:
                    logger.warning(f"Sessionid cookie error: {e}")
        
        # If no authenticated user found, DO NOT create a guest user.
        # Let Stripe handle guest checkout by passing customer_email.
        if not current_user or current_user.is_anonymous:
            logger.warning("No authenticated user found for checkout.")
            # We can proceed with a temporary customer email for Stripe if needed,
            # but we won't create a User object.
            # For this implementation, we will require login for checkout.
            return Response({'error': 'User authentication required for checkout.'}, status=401)

        else:
            logger.info(f"Using authenticated user: {current_user} (ID: {current_user.id})")
        
        # Get or create customer for authenticated user
        customer, created = Customer.objects.get_or_create(
            user=current_user,
            defaults={'phone': '', 'address': delivery_address}
        )
        logger.info(f"Customer: {customer} (ID: {customer.id}, created: {created})")
        
        # Build line items for Stripe
        line_items = []
        total_amount = 0
        
        for item_data in items:
            try:
                dish = Dish.objects.get(id=item_data['dish_id'])
                quantity = int(item_data['quantity'])
                price_cents = int(dish.price * 100)  # Convert to cents
                
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': dish.name,
                            'description': dish.description[:100] if dish.description else 'Delicious dish from our restaurant',
                        },
                        'unit_amount': price_cents,
                    },
                    'quantity': quantity,
                })
                total_amount += float(dish.price) * quantity
                
            except Dish.DoesNotExist:
                logger.warning(f"Dish not found: {item_data.get('dish_id')}")
                continue
        
        if not line_items:
            return Response({'error': 'No valid items found'}, status=400)
        
        # Add delivery fee
        delivery_fee_cents = 399  # $3.99
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Delivery Fee',
                    'description': 'Home delivery service',
                },
                'unit_amount': delivery_fee_cents,
            },
            'quantity': 1,
        })
        total_amount += 3.99
        
        # Create Stripe Checkout Session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url='http://localhost:5173/order-success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:5173/order-cancelled',
                metadata={
                    'customer_id': str(customer.id),
                    'user_id': str(current_user.id),
                    'user_email': str(current_user.email),
                    'delivery_address': delivery_address,
                    'special_instructions': special_instructions,
                    'items': json.dumps(items),
                    'total_amount': str(total_amount)
                },
                customer_email=current_user.email if current_user.email else None,
                billing_address_collection='required',
            )
            
            logger.info(f"Created Stripe session for customer {customer.id} (user: {current_user.username})")
            
            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'total_amount': total_amount
            })
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return Response({'error': f'Checkout error: {str(e)}'}, status=400)
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def stripe_success(request):
    """Handle successful payment redirect from Stripe"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        return Response({'error': 'No session ID provided'}, status=400)
    
    try:
        # Retrieve the checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            order, message = _create_order_from_stripe_session(session)
            
            if order:
                return Response({
                    'success': True,
                    'order_id': order.id,
                    'message': message,
                    'total_amount': order.total_amount
                })
            else:
                return Response({'error': message}, status=400)
        else:
            return Response({'error': 'Payment not completed'}, status=400)
            
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return Response({'error': 'Payment verification failed'}, status=400)
    except Exception as e:
        logger.error(f"Error processing success: {e}")
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def stripe_cancel(request):
    """Handle cancelled payment redirect from Stripe"""
    logger.info("Payment cancelled by user")
    return Response({
        'cancelled': True,
        'message': 'Payment was cancelled. You can try again when ready.'
    })

@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def get_stripe_config(request):
    """Get Stripe publishable key for frontend"""
    try:
        publishable_key = settings.STRIPE_PUBLISHABLE_KEY
        if not publishable_key:
            return Response({'error': 'Stripe not configured'}, status=500)
        
        return Response({
            'publishable_key': publishable_key,
            'success': True
        })
    except Exception as e:
        logger.error(f"Error getting Stripe config: {e}")
        return Response({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Stripe webhook event received: {event['type']}")
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return Response({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            _create_order_from_stripe_session(session)
            
        elif event['type'] == 'checkout.session.expired':
            session = event['data']['object']
            logger.info(f"Checkout session expired: {session['id']}")
            
        else:
            logger.info(f"Unhandled event type: {event['type']}")
            
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=400)
    
    return Response({'status': 'success'})

def _create_order_from_stripe_session(session):
    """
    Helper function to create an order from a Stripe session object.
    This avoids code duplication between webhook and success view.
    """
    metadata = session.get('metadata', {})
    customer_id = metadata.get('customer_id')
    delivery_address = metadata.get('delivery_address', '')
    special_instructions = metadata.get('special_instructions', '')
    items_json = metadata.get('items', '[]')
    total_amount = float(metadata.get('total_amount', 0))
    
    try:
        items = json.loads(items_json)
    except json.JSONDecodeError:
        items = []
    
    if not customer_id:
        logger.error("No customer_id in Stripe session metadata")
        return None, "Customer information missing"

    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        logger.error(f"Customer not found for customer_id: {customer_id}")
        return None, "Customer not found"
            
    # Check if order already exists
    existing_order = Order.objects.filter(
        customer=customer,
        total_amount=total_amount,
        payment_status='paid'
    ).order_by('-order_date').first()
    
    if existing_order:
        logger.info(f"Order #{existing_order.id} already exists for this payment.")
        return existing_order, "Order already created"

    # Create the order
    order = Order.objects.create(
        customer=customer,
        total_amount=total_amount,
        delivery_address=delivery_address,
        special_instructions=special_instructions,
        status='pending',  # As requested by user
        payment_status='paid'
    )
    
    # Create order items
    for item_data in items:
        try:
            dish = Dish.objects.get(id=item_data['dish_id'])
            OrderItem.objects.create(
                order=order,
                dish=dish,
                quantity=item_data['quantity'],
                price=dish.price,
                special_instructions=item_data.get('special_instructions', '')
            )
        except Dish.DoesNotExist:
            logger.warning(f"Dish with id {item_data.get('dish_id')} not found during order creation.")
            continue
            
    logger.info(f"Order #{order.id} created successfully for customer {customer.user.username}.")
    
    # Send notifications
    try:
        # To customer
        Notification.objects.create(
            user=customer.user,
            title="Order Received",
            message=f"Your order #{order.id} has been received and is now pending confirmation. Total: ${order.total_amount}",
            notification_type='order_placed'
        )
        # To admins
        send_notification_to_admins(
            title="New Order Alert",
            message=f"A new order #{order.id} has been placed by {customer.user.username} for ${order.total_amount}.",
            notification_type='order_placed'
        )
    except Exception as e:
        logger.error(f"Failed to send notifications for order #{order.id}: {e}")
    
    return order, "Order created successfully"
