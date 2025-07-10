from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from . import views

def api_root(request):
    """API Root - Welcome message and available endpoints"""
    return JsonResponse({
        'message': 'Restaurant API Server',
        'version': '1.0',
        'endpoints': {
            'admin_panel': '/admin/',
            'api_documentation': '/api/',
            'check_user_type': '/api/check-user-type/',
            'login': '/api/login/',
            'admin_login': '/api/admin/login/',
            'register': '/api/register/',
            'dishes': '/api/dishes/',
            'categories': '/api/categories/',
            'orders': '/api/orders/',
            'stripe_checkout': '/api/stripe/create-checkout-session/',
            'stripe_config': '/api/stripe/config/',
        },
        'status': 'Server is running successfully! 🚀'
    })

# Customer/Public API Router
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'dishes', views.DishViewSet)
router.register(r'restaurants', views.RestaurantViewSet)
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'ratings', views.DishRatingViewSet, basename='rating')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    # 🏠 Root path
    path('', api_root, name='api-root'),
    
    # 🌟 Public & Customer API
    path('api/', include(router.urls)),
    path('api/restaurant-info/', views.restaurant_info, name='restaurant-info'),
    path('api/menu-overview/', views.menu_overview, name='menu-overview'),
    path('api/homepage-stats/', views.homepage_stats, name='homepage-stats'),
    path('api/register/', views.register_user, name='register'),
    path('api/verify-email/<uidb64>/<token>/', views.verify_email, name='verify-email'),
    path('api/login/', views.customer_login, name='customer-login'),
    path('api/logout/', views.user_logout, name='user-logout'),
    path('api/profile/', views.user_profile, name='profile'),
    
    # 🔐 Authentication
    path('api-auth/', include('rest_framework.urls')),
    path('api/check-user-type/', views.check_user_type, name='check-user-type'),
    path('api/csrf-token/', views.get_csrf_token, name='csrf-token'),
    path('api/submit-rating/', views.submit_rating_simple, name='submit-rating'),
    path('api/add-rating/', views.add_rating, name='add-rating'),
    path('api/update-rating/<int:rating_id>/', views.update_rating, name='update-rating'),
    
    # 💳 Payment endpoints
    path('api/stripe/config/', views.get_stripe_config, name='stripe-config'),
    path('api/stripe/create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('api/stripe/success/', views.stripe_success, name='stripe-success'),
    path('api/stripe/cancel/', views.stripe_cancel, name='stripe-cancel'),
    path('api/stripe/webhook/', views.stripe_webhook, name='stripe-webhook'),
    
    # 📚 API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] 