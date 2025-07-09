from django.contrib import admin
from .models import Category, Dish, Customer, Order, OrderItem, DishRating, Restaurant, AdminProfile

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'admin_email', 'is_super_admin', 'created_at']
    list_filter = ['is_super_admin', 'created_at']
    search_fields = ['user__username', 'admin_email']
    list_editable = ['is_super_admin']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'is_spicy', 'is_vegetarian']
    list_filter = ['category', 'is_available', 'is_spicy', 'is_vegetarian', 'created_at']
    search_fields = ['name', 'description', 'ingredients']
    list_editable = ['is_available', 'price']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'phone']
    readonly_fields = ['created_at']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'order_date', 'status', 'payment_status', 'total_amount']
    list_filter = ['status', 'payment_status', 'order_date']
    search_fields = ['customer__user__first_name', 'customer__user__last_name']
    list_editable = ['status', 'payment_status']
    readonly_fields = ['order_date']
    inlines = [OrderItemInline]

@admin.register(DishRating)
class DishRatingAdmin(admin.ModelAdmin):
    list_display = ['dish', 'customer', 'rating', 'created_at']
    list_filter = ['rating', 'created_at', 'dish__category']
    search_fields = ['dish__name', 'customer__user__first_name']
    readonly_fields = ['created_at']

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'is_active', 'opening_time', 'closing_time']
    list_filter = ['is_active']
    search_fields = ['name', 'address']
    list_editable = ['is_active']
