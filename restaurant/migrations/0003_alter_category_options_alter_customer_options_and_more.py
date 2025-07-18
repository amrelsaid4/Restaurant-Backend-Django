# Generated by Django 5.2.2 on 2025-06-09 00:15

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0002_category_customer_dish_dishrating_order_orderitem_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ['name'], 'verbose_name': 'Category', 'verbose_name_plural': 'Categories'},
        ),
        migrations.AlterModelOptions(
            name='customer',
            options={'verbose_name': 'Customer', 'verbose_name_plural': 'Customers'},
        ),
        migrations.AlterModelOptions(
            name='dish',
            options={'ordering': ['category', 'name'], 'verbose_name': 'Dish', 'verbose_name_plural': 'Dishes'},
        ),
        migrations.AlterModelOptions(
            name='dishrating',
            options={'verbose_name': 'Dish Rating', 'verbose_name_plural': 'Dish Ratings'},
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-order_date'], 'verbose_name': 'Order', 'verbose_name_plural': 'Orders'},
        ),
        migrations.AlterModelOptions(
            name='orderitem',
            options={'verbose_name': 'Order Item', 'verbose_name_plural': 'Order Items'},
        ),
        migrations.AlterModelOptions(
            name='restaurant',
            options={'verbose_name': 'Restaurant', 'verbose_name_plural': 'Restaurants'},
        ),
        migrations.AlterField(
            model_name='category',
            name='description',
            field=models.TextField(blank=True, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='categories/', verbose_name='Category Image'),
        ),
        migrations.AlterField(
            model_name='category',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Category Name'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='address',
            field=models.TextField(verbose_name='Address'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True, verbose_name='Date of Birth'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='phone',
            field=models.CharField(max_length=15, verbose_name='Phone Number'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='calories',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Calories'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.category', verbose_name='Category'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='description',
            field=models.TextField(verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='dishes/', verbose_name='Dish Image'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='ingredients',
            field=models.TextField(blank=True, verbose_name='Ingredients'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='is_available',
            field=models.BooleanField(default=True, verbose_name='Available'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='is_spicy',
            field=models.BooleanField(default=False, verbose_name='Spicy'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='is_vegetarian',
            field=models.BooleanField(default=False, verbose_name='Vegetarian'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Dish Name'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='preparation_time',
            field=models.PositiveIntegerField(default=15, verbose_name='Preparation Time (minutes)'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Price'),
        ),
        migrations.AlterField(
            model_name='dishrating',
            name='comment',
            field=models.TextField(blank=True, verbose_name='Comment'),
        ),
        migrations.AlterField(
            model_name='dishrating',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.customer', verbose_name='Customer'),
        ),
        migrations.AlterField(
            model_name='dishrating',
            name='dish',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.dish', verbose_name='Dish'),
        ),
        migrations.AlterField(
            model_name='dishrating',
            name='rating',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Rating'),
        ),
        migrations.AlterField(
            model_name='order',
            name='actual_delivery_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Actual Delivery Time'),
        ),
        migrations.AlterField(
            model_name='order',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.customer', verbose_name='Customer'),
        ),
        migrations.AlterField(
            model_name='order',
            name='delivery_address',
            field=models.TextField(verbose_name='Delivery Address'),
        ),
        migrations.AlterField(
            model_name='order',
            name='estimated_delivery_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Estimated Delivery Time'),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Order Date'),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending', max_length=20, verbose_name='Payment Status'),
        ),
        migrations.AlterField(
            model_name='order',
            name='special_instructions',
            field=models.TextField(blank=True, verbose_name='Special Instructions'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('preparing', 'Preparing'), ('ready', 'Ready'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending', max_length=20, verbose_name='Order Status'),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Total Amount'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='dish',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.dish', verbose_name='Dish'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.order', verbose_name='Order'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Price'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='quantity',
            field=models.PositiveIntegerField(default=1, verbose_name='Quantity'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='special_instructions',
            field=models.TextField(blank=True, verbose_name='Special Instructions'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='address',
            field=models.TextField(verbose_name='Address'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='closing_time',
            field=models.TimeField(verbose_name='Closing Time'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='description',
            field=models.TextField(blank=True, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Email'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='restaurant/', verbose_name='Logo'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Restaurant Name'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='opening_time',
            field=models.TimeField(verbose_name='Opening Time'),
        ),
        migrations.AlterField(
            model_name='restaurant',
            name='phone',
            field=models.CharField(max_length=15, verbose_name='Phone Number'),
        ),
    ]
