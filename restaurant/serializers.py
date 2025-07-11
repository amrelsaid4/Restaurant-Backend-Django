from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import (
    Category, Dish, Customer, Order, OrderItem, 
    DishRating, Restaurant, AdminProfile, Notification, OrderAnalytics, ContactMessage
)
import logging

logger = logging.getLogger('restaurant')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class AdminProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = AdminProfile
        fields = ['id', 'user', 'admin_email', 'is_super_admin', 'created_at']

class CategorySerializer(serializers.ModelSerializer):
    dishes_count = serializers.SerializerMethodField()
    available_dishes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 'is_active', 
            'created_at', 'dishes_count', 'available_dishes_count'
        ]
    
    def get_dishes_count(self, obj):
        # استخدام cache للأداء
        cache_key = f'category_dishes_count_{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.dish_set.count()
            cache.set(cache_key, count, 300)  # 5 minutes
        return count
    
    def get_available_dishes_count(self, obj):
        cache_key = f'category_available_dishes_count_{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.dish_set.filter(is_available=True).count()
            cache.set(cache_key, count, 300)  # 5 minutes
        return count

class DishSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    price = serializers.FloatField()
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    rating_count = serializers.SerializerMethodField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    image = serializers.ImageField(max_length=None, use_url=True, required=False)

    class Meta:
        model = Dish
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'category', 'category_name',
            'image', 'is_available', 'stock_quantity', 'low_stock_threshold',
            'preparation_time', 'ingredients', 'calories', 'is_spicy',
            'is_vegetarian', 'average_rating', 'rating_count',
            'is_in_stock', 'is_low_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ('slug', 'category_name')

    def get_rating_count(self, obj):
        cache_key = f'dish_ratings_count_{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.dishrating_set.count()
            cache.set(cache_key, count, 300)  # 5 minutes
        return count

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value

class AdminDishSerializer(serializers.ModelSerializer):
    """
    A dedicated serializer for the Admin panel to handle dish creation and updates,
    especially for file uploads, without the complex read-only fields of the main serializer.
    """
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category'
    )

    class Meta:
        model = Dish
        fields = [
            'name', 'description', 'price', 'category_id', 'image', 'is_available',
            'stock_quantity', 'low_stock_threshold', 'preparation_time',
            'ingredients', 'calories', 'is_spicy', 'is_vegetarian'
        ]

class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'phone', 'address', 'date_of_birth', 'created_at', 'total_orders', 'total_spent']
    
    def get_total_orders(self, obj):
        return Order.objects.filter(customer=obj).count()
    
    def get_total_spent(self, obj):
        orders = Order.objects.filter(customer=obj, payment_status='paid')
        return sum(order.total_amount for order in orders)

class OrderItemSerializer(serializers.ModelSerializer):
    dish_name = serializers.CharField(source='dish.name', read_only=True)
    price = serializers.FloatField(source='dish.price', read_only=True) # Send as float

    class Meta:
        model = OrderItem
        fields = ['id', 'dish_name', 'quantity', 'price', 'special_instructions']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True, source='orderitem_set')
    customer = CustomerSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'order_date', 'status', 'status_display', 'payment_status',
            'total_amount', 'delivery_address', 'special_instructions',
            'estimated_delivery_time', 'actual_delivery_time', 'items'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'delivery_address', 'special_instructions', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        total_amount = 0
        for item_data in items_data:
            dish = Dish.objects.get(id=item_data['dish_id'])
            item_data['price'] = dish.price
            order_item = OrderItem.objects.create(order=order, **item_data)
            total_amount += order_item.total_price
        
        order.total_amount = total_amount
        order.save()
        return order

class DishRatingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.user.username', read_only=True)
    dish_name = serializers.CharField(source='dish.name', read_only=True)

    class Meta:
        model = DishRating
        fields = ['id', 'dish_name', 'customer_name', 'rating', 'comment', 'created_at']

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'address', 'phone', 'email',
            'opening_time', 'closing_time', 'is_active',
            'description', 'logo'
        ]

# إضافة Serializers للنماذج الجديدة
class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'title', 'message', 'notification_type',
            'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']

class OrderAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAnalytics
        fields = '__all__'


class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer for the ContactMessage model."""
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']

# تحسين OrderCreateSerializer مع validation
class EnhancedOrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'delivery_address', 'special_instructions', 'items'
        ]
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        
        for item_data in value:
            dish_id = item_data.get('dish_id')
            quantity = item_data.get('quantity', 0)
            
            try:
                dish = Dish.objects.get(id=dish_id)
                if not dish.is_available:
                    raise serializers.ValidationError(f"Dish '{dish.name}' is not available")
                if not dish.is_in_stock:
                    raise serializers.ValidationError(f"Dish '{dish.name}' is out of stock")
                if dish.stock_quantity < quantity:
                    raise serializers.ValidationError(
                        f"Insufficient stock for '{dish.name}'. Available: {dish.stock_quantity}"
                    )
            except Dish.DoesNotExist:
                raise serializers.ValidationError(f"Dish with id {dish_id} does not exist")
        
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        total_amount = 0
        for item_data in items_data:
            dish = Dish.objects.get(id=item_data['dish_id'])
            item_data['price'] = dish.price
            order_item = OrderItem.objects.create(order=order, **item_data)
            total_amount += order_item.total_price
            
            # تقليل المخزون
            dish.reduce_stock(item_data['quantity'])
        
        order.total_amount = total_amount
        order.save()
        
        logger.info(f"Order created successfully: #{order.id} - Total: ${total_amount}")
        return order 