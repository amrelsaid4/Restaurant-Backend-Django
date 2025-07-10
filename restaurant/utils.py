from django.core.cache import cache
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import logging
from django.utils.deprecation import MiddlewareMixin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
import six


from .models import Dish, Category, Order, OrderAnalytics, Notification

logger = logging.getLogger('restaurant')

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.is_active)
        )

account_activation_token_generator = AccountActivationTokenGenerator()

def send_verification_email(user, request):
    """
    Sends a verification email to the user with a unique token.
    """
    token = account_activation_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # The domain should be your frontend's domain
    # You might want to get this from settings or construct it dynamically
    frontend_domain = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    
    verification_url = f"{frontend_domain}/verify-email/{uid}/{token}/"
    
    subject = "Activate Your Restaurant Account"
    # For now, using a simple text message. An HTML template is better.
    # You will need to create 'account_activation_email.html'
    message = f"""
Hi {user.username},

Thank you for registering at our restaurant.
Please click the link below to activate your account:
{verification_url}

If you did not register, please ignore this email.

Best regards,
Restaurant Team
"""
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')

    try:
        send_mail(
            subject,
            message,
            from_email,
            [user.email],
            fail_silently=False,
        )
        
        # Check if using console backend
        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in email_backend:
            logger.info(f"Verification email sent to console for {user.email} (development mode)")
            logger.info(f"Verification URL: {verification_url}")
        else:
        logger.info(f"Verification email sent to {user.email}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


# ===== CACHING UTILITIES =====

def get_popular_dishes(limit=10):
    """الحصول على الأطباق الشعبية مع caching"""
    cache_key = f'popular_dishes_{limit}'
    dishes = cache.get(cache_key)
    
    if not dishes:
        from django.db.models import Count
        dishes = list(
            Dish.objects
            .filter(is_available=True)
            .annotate(order_count=Count('orderitem'))
            .order_by('-order_count')[:limit]
            .values('id', 'name', 'price', 'order_count')
        )
        cache.set(cache_key, dishes, 1800)  # 30 minutes
        logger.info(f"Popular dishes cached: {len(dishes)} items")
    
    return dishes

def get_category_stats():
    """إحصائيات الفئات مع caching"""
    cache_key = 'category_stats'
    stats = cache.get(cache_key)
    
    if not stats:
        stats = list(
            Category.objects
            .filter(is_active=True)
            .annotate(
                dishes_count=Count('dish'),
                available_dishes_count=Count('dish', filter=models.Q(dish__is_available=True))
            )
            .values('id', 'name', 'dishes_count', 'available_dishes_count')
        )
        cache.set(cache_key, stats, 900)  # 15 minutes
        logger.info(f"Category stats cached: {len(stats)} categories")
    
    return stats

def invalidate_dish_cache(dish_id):
    """إلغاء cache الطبق عند التحديث"""
    cache_keys = [
        f'dish_ratings_count_{dish_id}',
        'popular_dishes_10',
        'popular_dishes_5',
        'category_stats',
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info(f"Cache invalidated for dish {dish_id}")

# ===== NOTIFICATION UTILITIES =====

def create_notification(user, title, message, notification_type):
    """إنشاء إشعار جديد"""
    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type
        )
        logger.info(f"Notification created for user {user.username}: {title}")
        return notification
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None

def send_order_notifications(order):
    """إرسال إشعارات الطلب للعميل والإدارة"""
    # إشعار للعميل
    customer_notification = create_notification(
        user=order.customer.user,
        title="تم تأكيد طلبك",
        message=f"تم تأكيد طلبك رقم #{order.id} بقيمة ${order.total_amount}",
        notification_type="order_confirmed"
    )
    
    # إشعار للإدارة
    admin_users = User.objects.filter(is_staff=True)
    for admin in admin_users:
        admin_notification = create_notification(
            user=admin,
            title="طلب جديد",
            message=f"طلب جديد #{order.id} من {order.customer.user.get_full_name()}",
            notification_type="order_placed"
        )

def send_stock_alert(dish):
    """إرسال تنبيه انخفاض المخزون"""
    if dish.is_low_stock:
        admin_users = User.objects.filter(is_staff=True)
        for admin in admin_users:
            create_notification(
                user=admin,
                title="تنبيه: مخزون منخفض",
                message=f"الطبق '{dish.name}' مخزونه منخفض ({dish.stock_quantity} قطعة)",
                notification_type="stock_low"
            )

def send_notification_to_admins(title, message, notification_type):
    """Helper to send a notification to all staff users."""
    admin_users = User.objects.filter(is_staff=True)
    for admin in admin_users:
        create_notification(
            user=admin,
            title=title,
            message=message,
            notification_type=notification_type
        )

# ===== ANALYTICS UTILITIES =====

def calculate_daily_analytics(date=None):
    """حساب إحصائيات اليوم"""
    if not date:
        date = timezone.now().date()
    
    # الطلبات اليومية
    daily_orders = Order.objects.filter(
        order_date__date=date,
        payment_status='paid'
    )
    
    total_orders = daily_orders.count()
    total_revenue = daily_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # الأطباق الشعبية
    from django.db.models import Count
    popular_dishes = (
        daily_orders
        .values('orderitem__dish__name')
        .annotate(count=Count('orderitem__dish'))
        .order_by('-count')[:5]
    )
    
    popular_dishes_dict = {
        dish['orderitem__dish__name']: dish['count'] 
        for dish in popular_dishes
    }
    
    # حفظ أو تحديث الإحصائيات
    analytics, created = OrderAnalytics.objects.update_or_create(
        date=date,
        defaults={
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'avg_order_value': avg_order_value,
            'popular_dishes': popular_dishes_dict
        }
    )
    
    logger.info(f"Daily analytics calculated for {date}: {total_orders} orders, ${total_revenue} revenue")
    return analytics

def get_weekly_stats():
    """إحصائيات الأسبوع"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    weekly_analytics = OrderAnalytics.objects.filter(
        date__range=[start_date, end_date]
    ).aggregate(
        total_orders=Sum('total_orders'),
        total_revenue=Sum('total_revenue'),
        avg_order_value=Avg('avg_order_value')
    )
    
    return weekly_analytics

def get_monthly_stats():
    """إحصائيات الشهر"""
    end_date = timezone.now().date()
    start_date = end_date.replace(day=1)
    
    monthly_analytics = OrderAnalytics.objects.filter(
        date__range=[start_date, end_date]
    ).aggregate(
        total_orders=Sum('total_orders'),
        total_revenue=Sum('total_revenue'),
        avg_order_value=Avg('avg_order_value')
    )
    
    return monthly_analytics

# ===== IMAGE OPTIMIZATION =====

def optimize_image(image_field):
    """ضغط وتحسين الصور"""
    try:
        from PIL import Image
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import io
        
        img = Image.open(image_field)
        
        # تحويل إلى RGB إذا لزم الأمر
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # تصغير الحجم
        img.thumbnail((800, 600), Image.LANCZOS)
        
        # ضغط الصورة
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        # إنشاء ملف جديد
        optimized_image = InMemoryUploadedFile(
            output, 'ImageField', 
            f"{image_field.name.split('.')[0]}.jpg",
            'image/jpeg', output.getbuffer().nbytes, None
        )
        
        logger.info(f"Image optimized: {image_field.name}")
        return optimized_image
        
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return image_field

# ===== VALIDATION UTILITIES =====

def validate_email_unique(email):
    """التحقق من فرادة البريد الإلكتروني"""
    from django.contrib.auth.models import User
    return not User.objects.filter(email=email).exists()

def validate_order_items(items):
    """التحقق من صحة عناصر الطلب"""
    errors = []
    
    for item in items:
        dish_id = item.get('dish_id')
        quantity = item.get('quantity', 0)
        
        try:
            dish = Dish.objects.get(id=dish_id)
            
            if not dish.is_available:
                errors.append(f"Dish '{dish.name}' is not available")
            
            if not dish.is_in_stock:
                errors.append(f"Dish '{dish.name}' is out of stock")
            
            if dish.stock_quantity < quantity:
                errors.append(f"Insufficient stock for '{dish.name}'. Available: {dish.stock_quantity}")
                
        except Dish.DoesNotExist:
            errors.append(f"Dish with id {dish_id} does not exist")
    
    return errors 