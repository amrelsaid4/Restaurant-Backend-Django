from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Admin API Router
admin_router = DefaultRouter()
admin_router.register(r'categories', views.AdminCategoryViewSet, basename='admin-category')
admin_router.register(r'dishes', views.AdminDishViewSet, basename='admin-dish')
admin_router.register(r'orders', views.AdminOrderViewSet, basename='admin-order')
admin_router.register(r'customers', views.AdminCustomerViewSet, basename='admin-customer')
admin_router.register(r'restaurants', views.AdminRestaurantViewSet, basename='admin-restaurant')
admin_router.register(r'analytics', views.OrderAnalyticsViewSet, basename='admin-analytics')

# The urlpatterns for the admin API
urlpatterns = [
    path('dashboard/', views.admin_dashboard_stats, name='admin-dashboard'),
    path('login/', views.admin_login, name='admin-login'),
    # The router URLs are included at the end
    path('', include(admin_router.urls)),
] 