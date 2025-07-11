# Generated by Django 5.2.2 on 2025-06-09 00:04

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='اسم التصنيف')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('image', models.ImageField(blank=True, null=True, upload_to='categories/', verbose_name='صورة التصنيف')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'تصنيف',
                'verbose_name_plural': 'التصنيفات',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=15, verbose_name='رقم الهاتف')),
                ('address', models.TextField(verbose_name='العنوان')),
                ('date_of_birth', models.DateField(blank=True, null=True, verbose_name='تاريخ الميلاد')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'عميل',
                'verbose_name_plural': 'العملاء',
            },
        ),
        migrations.CreateModel(
            name='Dish',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='اسم الطبق')),
                ('description', models.TextField(verbose_name='الوصف')),
                ('price', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='السعر')),
                ('image', models.ImageField(blank=True, null=True, upload_to='dishes/', verbose_name='صورة الطبق')),
                ('is_available', models.BooleanField(default=True, verbose_name='متوفر')),
                ('preparation_time', models.PositiveIntegerField(default=15, verbose_name='وقت التحضير (دقيقة)')),
                ('ingredients', models.TextField(blank=True, verbose_name='المكونات')),
                ('calories', models.PositiveIntegerField(blank=True, null=True, verbose_name='السعرات الحرارية')),
                ('is_spicy', models.BooleanField(default=False, verbose_name='حار')),
                ('is_vegetarian', models.BooleanField(default=False, verbose_name='نباتي')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.category', verbose_name='التصنيف')),
            ],
            options={
                'verbose_name': 'طبق',
                'verbose_name_plural': 'الأطباق',
                'ordering': ['category', 'name'],
            },
        ),
        migrations.CreateModel(
            name='DishRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='التقييم')),
                ('comment', models.TextField(blank=True, verbose_name='التعليق')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.customer', verbose_name='العميل')),
                ('dish', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.dish', verbose_name='الطبق')),
            ],
            options={
                'verbose_name': 'تقييم الطبق',
                'verbose_name_plural': 'تقييمات الأطباق',
                'unique_together': {('dish', 'customer')},
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_date', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الطلب')),
                ('status', models.CharField(choices=[('pending', 'في الانتظار'), ('confirmed', 'مؤكد'), ('preparing', 'قيد التحضير'), ('ready', 'جاهز'), ('delivered', 'تم التوصيل'), ('cancelled', 'ملغى')], default='pending', max_length=20, verbose_name='حالة الطلب')),
                ('payment_status', models.CharField(choices=[('pending', 'في الانتظار'), ('paid', 'مدفوع'), ('failed', 'فشل الدفع'), ('refunded', 'مسترد')], default='pending', max_length=20, verbose_name='حالة الدفع')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='المبلغ الإجمالي')),
                ('delivery_address', models.TextField(verbose_name='عنوان التوصيل')),
                ('special_instructions', models.TextField(blank=True, verbose_name='تعليمات خاصة')),
                ('estimated_delivery_time', models.DateTimeField(blank=True, null=True, verbose_name='وقت التوصيل المتوقع')),
                ('actual_delivery_time', models.DateTimeField(blank=True, null=True, verbose_name='وقت التوصيل الفعلي')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.customer', verbose_name='العميل')),
            ],
            options={
                'verbose_name': 'طلب',
                'verbose_name_plural': 'الطلبات',
                'ordering': ['-order_date'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='الكمية')),
                ('price', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='السعر')),
                ('special_instructions', models.TextField(blank=True, verbose_name='تعليمات خاصة')),
                ('dish', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.dish', verbose_name='الطبق')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='restaurant.order', verbose_name='الطلب')),
            ],
            options={
                'verbose_name': 'عنصر الطلب',
                'verbose_name_plural': 'عناصر الطلب',
            },
        ),
        migrations.CreateModel(
            name='Restaurant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='اسم المطعم')),
                ('address', models.TextField(verbose_name='العنوان')),
                ('phone', models.CharField(max_length=15, verbose_name='رقم الهاتف')),
                ('email', models.EmailField(max_length=254, verbose_name='البريد الإلكتروني')),
                ('opening_time', models.TimeField(verbose_name='وقت الفتح')),
                ('closing_time', models.TimeField(verbose_name='وقت الإغلاق')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='restaurant/', verbose_name='الشعار')),
            ],
            options={
                'verbose_name': 'مطعم',
                'verbose_name_plural': 'المطاعم',
            },
        ),
        migrations.DeleteModel(
            name='MenuItem',
        ),
    ]
