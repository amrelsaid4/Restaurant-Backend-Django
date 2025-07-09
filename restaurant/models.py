from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import logging

# إعداد الـ logger
logger = logging.getLogger('restaurant')

# Admin Profile for managing admin users
class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="User")
    is_super_admin = models.BooleanField(default=False, verbose_name="Super Admin")
    admin_email = models.EmailField(unique=True, verbose_name="Admin Email")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"
    
    def __str__(self):
        return f"Admin: {self.user.username} ({self.admin_email})"
    
    @classmethod
    def is_admin_email(cls, email):
        """Check if email belongs to an admin"""
        return cls.objects.filter(admin_email=email).exists()

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Category Name")
    slug = models.SlugField(blank=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Category Image")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
        # إضافة فهارس للأداء
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        logger.info(f"Category saved: {self.name}")
        super().save(*args, **kwargs)

    def clean(self):
        if Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({'slug': 'Category with this slug already exists'})

    def __str__(self):
        return self.name

class Dish(models.Model):
    name = models.CharField(max_length=100, verbose_name="Dish Name")
    slug = models.SlugField(blank=True, verbose_name="Slug")
    description = models.TextField(verbose_name="Description")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Price")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Category")
    image = models.ImageField(upload_to='dishes/', blank=True, null=True, verbose_name="Dish Image")
    is_available = models.BooleanField(default=True, verbose_name="Available")
    # إضافة Stock Management
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="Stock Quantity")
    low_stock_threshold = models.PositiveIntegerField(default=5, verbose_name="Low Stock Alert")
    preparation_time = models.PositiveIntegerField(default=15, verbose_name="Preparation Time (minutes)")
    ingredients = models.TextField(blank=True, verbose_name="Ingredients")
    calories = models.PositiveIntegerField(blank=True, null=True, verbose_name="Calories")
    is_spicy = models.BooleanField(default=False, verbose_name="Spicy")
    is_vegetarian = models.BooleanField(default=False, verbose_name="Vegetarian")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dish"
        verbose_name_plural = "Dishes"
        ordering = ['category', 'name']
        # إضافة فهارس محسنة للأداء
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['created_at']),
            models.Index(fields=['price']),
            models.Index(fields=['slug']),
            models.Index(fields=['stock_quantity']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        logger.info(f"Dish saved: {self.name} - Stock: {self.stock_quantity}")
        super().save(*args, **kwargs)

    def clean(self):
        if Dish.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({'slug': 'Dish with this slug already exists'})
        if self.price <= 0:
            raise ValidationError({'price': 'Price must be greater than 0'})

    @property
    def is_low_stock(self):
        """Check if dish is low on stock"""
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def is_in_stock(self):
        """Check if dish is in stock"""
        return self.stock_quantity > 0

    def reduce_stock(self, quantity):
        """Reduce stock when order is placed"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save()
            logger.info(f"Stock reduced for {self.name}: {quantity} units")
            return True
        else:
            logger.warning(f"Insufficient stock for {self.name}. Available: {self.stock_quantity}, Requested: {quantity}")
            return False

    def __str__(self):
        return f"{self.name} - ${self.price}"

    @property
    def average_rating(self):
        ratings = self.dishrating_set.all()
        if ratings:
            return sum([r.rating for r in ratings]) / len(ratings)
        return 0

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="User")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    address = models.TextField(verbose_name="Address")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    is_phone_verified = models.BooleanField(default=False, verbose_name="Phone Verified")
    is_email_verified = models.BooleanField(default=False, verbose_name="Email Verified")
    phone_verification_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Phone Verification Code")
    email_verification_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Email Verification Code")
    verification_code_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Verification Code Expires At")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Customer")
    order_date = models.DateTimeField(auto_now_add=True, verbose_name="Order Date")
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending', verbose_name="Order Status")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name="Payment Status")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Amount")
    delivery_address = models.TextField(verbose_name="Delivery Address")
    special_instructions = models.TextField(blank=True, verbose_name="Special Instructions")
    estimated_delivery_time = models.DateTimeField(blank=True, null=True, verbose_name="Estimated Delivery Time")
    actual_delivery_time = models.DateTimeField(blank=True, null=True, verbose_name="Actual Delivery Time")

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-order_date']
        # إضافة فهارس للأداء
        indexes = [
            models.Index(fields=['order_date']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['customer', 'order_date']),
        ]

    def save(self, *args, **kwargs):
        logger.info(f"Order saved: #{self.id} - Customer: {self.customer} - Total: ${self.total_amount}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.customer} - ${self.total_amount}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Order")
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, verbose_name="Dish")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Price")
    special_instructions = models.TextField(blank=True, verbose_name="Special Instructions")

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.dish.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity

class DishRating(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, verbose_name="Dish")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Customer")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Rating"
    )
    comment = models.TextField(blank=True, verbose_name="Comment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dish Rating"
        verbose_name_plural = "Dish Ratings"
        # Removed unique_together to allow multiple ratings from same customer

    def __str__(self):
        return f"{self.dish.name} - {self.rating} stars"

class Restaurant(models.Model):
    name = models.CharField(max_length=100, verbose_name="Restaurant Name")
    address = models.TextField(verbose_name="Address")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    email = models.EmailField(verbose_name="Email")
    opening_time = models.TimeField(verbose_name="Opening Time")
    closing_time = models.TimeField(verbose_name="Closing Time")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    description = models.TextField(blank=True, verbose_name="Description")
    logo = models.ImageField(upload_to='restaurant/', blank=True, null=True, verbose_name="Logo")

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"

    def __str__(self):
        return self.name

# MenuItem - keeping for backward compatibility, now points to Dish
MenuItem = Dish

# إضافة نموذج الإشعارات
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_preparing', 'Order Preparing'),
        ('order_ready', 'Order Ready'),
        ('order_delivered', 'Order Delivered'),
        ('stock_low', 'Stock Low'),
        ('payment_received', 'Payment Received'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    title = models.CharField(max_length=200, verbose_name="Title")
    message = models.TextField(verbose_name="Message")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="Type")
    is_read = models.BooleanField(default=False, verbose_name="Read")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

# إضافة نموذج التحليلات
class OrderAnalytics(models.Model):
    date = models.DateField(verbose_name="Date")
    total_orders = models.IntegerField(default=0, verbose_name="Total Orders")
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Revenue")
    popular_dishes = models.JSONField(default=dict, verbose_name="Popular Dishes")
    avg_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Average Order Value")
    
    class Meta:
        verbose_name = "Order Analytics"
        verbose_name_plural = "Order Analytics"
        ordering = ['-date']
        unique_together = ['date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Analytics {self.date} - {self.total_orders} orders"
