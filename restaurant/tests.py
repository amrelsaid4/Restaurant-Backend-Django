from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

from .models import Category, Dish, Customer, Order, OrderItem, DishRating


class DishAPITestCase(APITestCase):
    """اختبار API الأطباق"""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category",
            description="Test description"
        )
        self.dish = Dish.objects.create(
            name="Test Dish",
            slug="test-dish",
            description="Test dish description",
            price=Decimal('15.99'),
            category=self.category,
            stock_quantity=10
        )
    
    def test_dish_list(self):
        """اختبار استعراض قائمة الأطباق"""
        url = reverse('dish-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Dish")
    
    def test_dish_filter_by_category(self):
        """اختبار فلترة الأطباق حسب الفئة"""
        url = reverse('dish-list')
        response = self.client.get(url, {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_dish_search(self):
        """اختبار البحث في الأطباق"""
        url = reverse('dish-list')
        response = self.client.get(url, {'search': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Dish")
    
    def test_popular_dishes(self):
        """اختبار الأطباق الشعبية"""
        url = reverse('dish-popular')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class OrderAPITestCase(APITestCase):
    """اختبار API الطلبات"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone='123456789',
            address='Test Address'
        )
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )
        self.dish = Dish.objects.create(
            name="Test Dish",
            slug="test-dish",
            description="Test description",
            price=Decimal('15.99'),
            category=self.category,
            stock_quantity=10
        )
    
    def test_create_order_authenticated(self):
        """اختبار إنشاء طلب مع مستخدم مصادق عليه"""
        self.client.force_authenticate(user=self.user)
        
        order_data = {
            'delivery_address': 'Test Delivery Address',
            'special_instructions': 'Test instructions',
            'items': [
                {
                    'dish_id': self.dish.id,
                    'quantity': 2,
                    'special_instructions': 'No spice'
                }
            ]
        }
        
        url = reverse('order-list')
        response = self.client.post(url, order_data, format='json')
        self.assertEqual(response.status_code, 201)
    
    def test_create_order_insufficient_stock(self):
        """اختبار إنشاء طلب بمخزون غير كافي"""
        self.client.force_authenticate(user=self.user)
        
        order_data = {
            'delivery_address': 'Test Address',
            'items': [
                {
                    'dish_id': self.dish.id,
                    'quantity': 20,  # أكثر من المخزون المتاح
                }
            ]
        }
        
        url = reverse('order-list')
        response = self.client.post(url, order_data, format='json')
        self.assertEqual(response.status_code, 400)


class CategoryModelTestCase(TestCase):
    """اختبار نموذج الفئات"""
    
    def test_category_creation(self):
        """اختبار إنشاء فئة"""
        category = Category.objects.create(
            name="Test Category",
            description="Test description"
        )
        self.assertEqual(category.name, "Test Category")
        self.assertEqual(category.slug, "test-category")
    
    def test_category_str(self):
        """اختبار تمثيل الفئة كنص"""
        category = Category.objects.create(name="Pizza")
        self.assertEqual(str(category), "Pizza")


class DishModelTestCase(TestCase):
    """اختبار نموذج الأطباق"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )
    
    def test_dish_creation(self):
        """اختبار إنشاء طبق"""
        dish = Dish.objects.create(
            name="Test Dish",
            description="Test description",
            price=Decimal('15.99'),
            category=self.category,
            stock_quantity=10
        )
        self.assertEqual(dish.name, "Test Dish")
        self.assertEqual(dish.slug, "test-dish")
        self.assertTrue(dish.is_in_stock)
    
    def test_stock_management(self):
        """اختبار إدارة المخزون"""
        dish = Dish.objects.create(
            name="Test Dish",
            price=Decimal('15.99'),
            category=self.category,
            stock_quantity=10,
            low_stock_threshold=5
        )
        
        # تقليل المخزون
        result = dish.reduce_stock(3)
        self.assertTrue(result)
        self.assertEqual(dish.stock_quantity, 7)
        
        # محاولة تقليل مخزون أكثر من المتاح
        result = dish.reduce_stock(15)
        self.assertFalse(result)
        self.assertEqual(dish.stock_quantity, 7)
    
    def test_low_stock_alert(self):
        """اختبار تنبيه المخزون المنخفض"""
        dish = Dish.objects.create(
            name="Test Dish",
            price=Decimal('15.99'),
            category=self.category,
            stock_quantity=3,
            low_stock_threshold=5
        )
        self.assertTrue(dish.is_low_stock)
