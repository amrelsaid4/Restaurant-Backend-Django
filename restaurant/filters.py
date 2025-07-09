import django_filters
from django_filters import rest_framework as filters
from django.db.models import Q, F
from .models import Dish, Category, Order, DishRating

class DishFilter(filters.FilterSet):
    """فلاتر متقدمة للأطباق"""
    
    # فلترة حسب السعر
    price_min = filters.NumberFilter(field_name="price", lookup_expr='gte')
    price_max = filters.NumberFilter(field_name="price", lookup_expr='lte')
    price_range = filters.RangeFilter(field_name="price")
    
    # فلترة حسب السعرات الحرارية
    calories_min = filters.NumberFilter(field_name="calories", lookup_expr='gte')
    calories_max = filters.NumberFilter(field_name="calories", lookup_expr='lte')
    
    # فلترة حسب وقت التحضير
    prep_time_max = filters.NumberFilter(field_name="preparation_time", lookup_expr='lte')
    
    # بحث في النص
    search = filters.CharFilter(method='filter_search')
    
    # فلترة حسب التوفر والمخزون
    in_stock = filters.BooleanFilter(method='filter_in_stock')
    low_stock = filters.BooleanFilter(method='filter_low_stock')
    
    # فلترة حسب التقييم
    min_rating = filters.NumberFilter(method='filter_min_rating')
    
    class Meta:
        model = Dish
        fields = {
            'category': ['exact'],
            'is_vegetarian': ['exact'],
            'is_spicy': ['exact'],
            'is_available': ['exact'],
            'created_at': ['gte', 'lte'],
        }
    
    def filter_search(self, queryset, name, value):
        """بحث في اسم الطبق والمكونات والوصف"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(ingredients__icontains=value)
        )
    
    def filter_in_stock(self, queryset, name, value):
        """فلترة الأطباق المتوفرة في المخزون"""
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)
    
    def filter_low_stock(self, queryset, name, value):
        """فلترة الأطباق ذات المخزون المنخفض"""
        if value:
            return queryset.filter(stock_quantity__lte=F('low_stock_threshold'))
        return queryset
    
    def filter_min_rating(self, queryset, name, value):
        """فلترة حسب الحد الأدنى للتقييم"""
        from django.db.models import Avg
        return queryset.annotate(
            avg_rating=Avg('dishrating__rating')
        ).filter(avg_rating__gte=value)

class CategoryFilter(filters.FilterSet):
    """فلاتر للفئات"""
    
    search = filters.CharFilter(method='filter_search')
    has_dishes = filters.BooleanFilter(method='filter_has_dishes')
    
    class Meta:
        model = Category
        fields = {
            'is_active': ['exact'],
            'created_at': ['gte', 'lte'],
        }
    
    def filter_search(self, queryset, name, value):
        """بحث في اسم الفئة والوصف"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value)
        )
    
    def filter_has_dishes(self, queryset, name, value):
        """فلترة الفئات التي تحتوي على أطباق"""
        if value:
            return queryset.filter(dish__isnull=False).distinct()
        return queryset.filter(dish__isnull=True)

class OrderFilter(filters.FilterSet):
    """فلاتر للطلبات"""
    
    # فلترة حسب التاريخ
    date_from = filters.DateFilter(field_name="order_date", lookup_expr='gte')
    date_to = filters.DateFilter(field_name="order_date", lookup_expr='lte')
    
    # فلترة حسب المبلغ
    amount_min = filters.NumberFilter(field_name="total_amount", lookup_expr='gte')
    amount_max = filters.NumberFilter(field_name="total_amount", lookup_expr='lte')
    
    # بحث في العنوان
    address_search = filters.CharFilter(field_name="delivery_address", lookup_expr='icontains')
    
    class Meta:
        model = Order
        fields = {
            'status': ['exact', 'in'],
            'payment_status': ['exact', 'in'],
            'customer': ['exact'],
        }

class DishRatingFilter(filters.FilterSet):
    """فلاتر للتقييمات"""
    
    rating_min = filters.NumberFilter(field_name="rating", lookup_expr='gte')
    rating_max = filters.NumberFilter(field_name="rating", lookup_expr='lte')
    
    # بحث في التعليقات
    comment_search = filters.CharFilter(field_name="comment", lookup_expr='icontains')
    
    class Meta:
        model = DishRating
        fields = {
            'rating': ['exact'],
            'dish': ['exact'],
            'customer': ['exact'],
            'created_at': ['gte', 'lte'],
        } 