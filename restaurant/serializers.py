from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import (
    Category, Dish, Customer, Order, OrderItem, 
    DishRating, Restaurant, AdminProfile, Notification, OrderAnalytics
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
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    average_rating = serializers.ReadOnlyField()
    rating_count = serializers.SerializerMethodField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    image = serializers.ImageField(max_length=None, use_url=True, required=False)
    
    class Meta:
        model = Dish
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'category', 'category_id',
            'image', 'is_available', 'stock_quantity', 'low_stock_threshold',
            'preparation_time', 'ingredients', 'calories', 'is_spicy', 
            'is_vegetarian', 'average_rating', 'rating_count',
            'is_in_stock', 'is_low_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ('slug',)
    
    def get_rating_count(self, obj):
        cache_key = f'dish_ratings_count_{obj.id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.dishrating_set.count()
            cache.set(cache_key, count, 300)  # 5 minutes
        return count

    def to_representation(self, instance):
        """Convert `image` to a full URL."""
        representation = super().to_representation(instance)
        if instance.image:
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(instance.image.url)
            else:
                representation['image'] = instance.image.url
        else:
            representation['image'] = None # Ensure image is null if not set
        return representation
    
    def update(self, instance, validated_data):
        # Handle image update properly - only pop if it's not provided or is None
        if 'image' in validated_data and validated_data['image'] is None:
            validated_data.pop('image')
        return super().update(instance, validated_data)
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value
    
    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value

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
    dish = DishSerializer(read_only=True)
    dish_id = serializers.IntegerField(write_only=True)
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'dish', 'dish_id', 'quantity', 'price', 'special_instructions', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'order_date', 'status', 'payment_status',
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
    customer = CustomerSerializer(read_only=True)
    dish = DishSerializer(read_only=True)
    dish_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DishRating
        fields = ['id', 'dish', 'dish_id', 'customer', 'rating', 'comment', 'created_at']

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
        fields = [
            'id', 'date', 'total_orders', 'total_revenue',
            'popular_dishes', 'avg_order_value'
        ]

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