from django.core.management.base import BaseCommand
from restaurant.models import Dish, Category, DishRating, OrderItem
from django.db import transaction


class Command(BaseCommand):
    help = 'Clear all dishes and categories from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR('This will delete ALL dishes and categories!')
            )
            self.stdout.write(
                self.style.WARNING('Run with --confirm flag to proceed: python manage.py clear_all_data --confirm')
            )
            return

        try:
            with transaction.atomic():
                # Delete in correct order due to foreign key constraints
                dish_ratings_count = DishRating.objects.count()
                order_items_count = OrderItem.objects.count()
                dishes_count = Dish.objects.count()
                categories_count = Category.objects.count()

                # Clear dish ratings first
                DishRating.objects.all().delete()
                self.stdout.write(f'Deleted {dish_ratings_count} dish ratings')

                # Clear order items that reference dishes
                OrderItem.objects.all().delete()
                self.stdout.write(f'Deleted {order_items_count} order items')

                # Clear all dishes
                Dish.objects.all().delete()
                self.stdout.write(f'Deleted {dishes_count} dishes')

                # Clear all categories
                Category.objects.all().delete()
                self.stdout.write(f'Deleted {categories_count} categories')

                self.stdout.write(
                    self.style.SUCCESS('✅ Successfully cleared all dishes and categories!')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error clearing data: {str(e)}')
            ) 