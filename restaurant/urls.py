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

# Admin API Router
admin_router = DefaultRouter()
admin_router.register(r'categories', views.AdminCategoryViewSet, basename='admin-category')
admin_router.register(r'dishes', views.AdminDishViewSet, basename='admin-dish')
admin_router.register(r'orders', views.AdminOrderViewSet, basename='admin-order')
admin_router.register(r'customers', views.AdminCustomerViewSet, basename='admin-customer')
admin_router.register(r'restaurants', views.AdminRestaurantViewSet, basename='admin-restaurant')
admin_router.register(r'analytics', views.OrderAnalyticsViewSet, basename='admin-analytics')

urlpatterns = [
    # 🏠 Root path
    path('', api_root, name='api-root'),
    
    # 🌟 Public & Customer API
    path('api/', include(router.urls)),
    path('api/restaurant-info/', views.restaurant_info, name='restaurant-info'),
    path('api/menu-overview/', views.menu_overview, name='menu-overview'),
    path('api/homepage-stats/', views.homepage_stats, name='homepage-stats'),
    path('api/register/', views.register_user, name='register'),
    path('api/send-verification/', views.send_verification_code, name='send-verification'),
    path('api/verify-code/', views.verify_code, name='verify-code'),
    path('api/login/', views.customer_login, name='customer-login'),
    path('api/logout/', views.user_logout, name='user-logout'),
    path('api/profile/', views.user_profile, name='profile'),
    
    # 🛡️ Admin API
    path('api/admin/', include(admin_router.urls)),
    path('api/admin/dashboard/', views.admin_dashboard_stats, name='admin-dashboard'),
    path('api/admin/login/', views.admin_login, name='admin-login'),
    
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