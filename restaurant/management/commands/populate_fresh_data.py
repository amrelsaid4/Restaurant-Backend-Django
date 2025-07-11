from django.core.management.base import BaseCommand
from restaurant.models import Dish, Category
from django.db import transaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate fresh dishes and categories with Cloudinary images'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Create Categories
                categories_data = [
                    {
                        'name': 'Burgers', 
                        'description': 'Delicious handcrafted burgers',
                        'slug': 'burgers'
                    },
                    {
                        'name': 'Beverages', 
                        'description': 'Refreshing drinks and smoothies', 
                        'slug': 'beverages'
                    },
                    {
                        'name': 'Salads', 
                        'description': 'Fresh and healthy salads', 
                        'slug': 'salads'
                    },
                    {
                        'name': 'Desserts', 
                        'description': 'Sweet treats and desserts', 
                        'slug': 'desserts'
                    },
                    {
                        'name': 'Main Dishes', 
                        'description': 'Hearty main course dishes', 
                        'slug': 'main-dishes'
                    },
                ]

                categories = {}
                for cat_data in categories_data:
                    category = Category.objects.create(**cat_data)
                    categories[cat_data['name']] = category
                    self.stdout.write(f'✅ Created category: {category.name}')

                # Create Dishes with Cloudinary images
                dishes_data = [
                    # Burgers
                    {
                        'name': 'Classic Cheeseburger',
                        'description': 'Juicy beef patty with cheese, lettuce, tomato, and special sauce',
                        'price': Decimal('12.99'),
                        'category': categories['Burgers'],
                        'image': 'dishes/classic-cheeseburger.jpg',
                        'ingredients': 'Beef patty, cheese, lettuce, tomato, onion, special sauce',
                        'is_available': True,
                        'is_vegetarian': False,
                        'is_spicy': False,
                        'preparation_time': 15,
                        'stock_quantity': 50,
                    },
                    {
                        'name': 'Bacon Deluxe Burger',
                        'description': 'Premium burger with crispy bacon and avocado',
                        'price': Decimal('15.99'),
                        'category': categories['Burgers'],
                        'image': 'dishes/bacon-deluxe-burger.jpg',
                        'ingredients': 'Beef patty, bacon, avocado, cheese, lettuce, tomato',
                        'is_available': True,
                        'is_vegetarian': False,
                        'is_spicy': False,
                        'preparation_time': 18,
                        'stock_quantity': 40,
                    },
                    {
                        'name': 'Veggie Burger',
                        'description': 'Plant-based patty with fresh vegetables',
                        'price': Decimal('11.99'),
                        'category': categories['Burgers'],
                        'image': 'dishes/veggie-burger.jpg',
                        'ingredients': 'Plant-based patty, lettuce, tomato, onion, vegan mayo',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 12,
                        'stock_quantity': 30,
                    },

                    # Beverages
                    {
                        'name': 'Fresh Orange Juice',
                        'description': 'Freshly squeezed orange juice',
                        'price': Decimal('4.99'),
                        'category': categories['Beverages'],
                        'image': 'dishes/orange-juice.jpg',
                        'ingredients': 'Fresh oranges',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 3,
                        'stock_quantity': 100,
                    },
                    {
                        'name': 'Mango Smoothie',
                        'description': 'Creamy mango smoothie with yogurt',
                        'price': Decimal('6.99'),
                        'category': categories['Beverages'],
                        'image': 'dishes/mango-smoothie.jpg',
                        'ingredients': 'Mango, yogurt, honey, ice',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 5,
                        'stock_quantity': 80,
                    },
                    {
                        'name': 'Cola',
                        'description': 'Classic cola drink',
                        'price': Decimal('2.99'),
                        'category': categories['Beverages'],
                        'image': 'dishes/cola.jpg',
                        'ingredients': 'Carbonated water, cola flavoring',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 1,
                        'stock_quantity': 200,
                    },

                    # Salads
                    {
                        'name': 'Caesar Salad',
                        'description': 'Classic Caesar salad with croutons and parmesan',
                        'price': Decimal('9.99'),
                        'category': categories['Salads'],
                        'image': 'dishes/caesar-salad.jpg',
                        'ingredients': 'Romaine lettuce, parmesan cheese, croutons, Caesar dressing',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 8,
                        'stock_quantity': 60,
                    },
                    {
                        'name': 'Greek Salad',
                        'description': 'Fresh Mediterranean salad with feta cheese',
                        'price': Decimal('10.99'),
                        'category': categories['Salads'],
                        'image': 'dishes/greek-salad.jpg',
                        'ingredients': 'Tomatoes, cucumbers, olives, feta cheese, olive oil',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 7,
                        'stock_quantity': 50,
                    },

                    # Desserts
                    {
                        'name': 'Chocolate Cake',
                        'description': 'Rich chocolate cake with chocolate frosting',
                        'price': Decimal('7.99'),
                        'category': categories['Desserts'],
                        'image': 'dishes/chocolate-cake.jpg',
                        'ingredients': 'Chocolate, flour, sugar, eggs, butter',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 10,
                        'stock_quantity': 25,
                    },
                    {
                        'name': 'Tiramisu',
                        'description': 'Classic Italian tiramisu dessert',
                        'price': Decimal('8.99'),
                        'category': categories['Desserts'],
                        'image': 'dishes/tiramisu.jpg',
                        'ingredients': 'Mascarpone, coffee, ladyfingers, cocoa powder',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 12,
                        'stock_quantity': 20,
                    },
                    {
                        'name': 'Vanilla Ice Cream',
                        'description': 'Creamy vanilla ice cream',
                        'price': Decimal('4.99'),
                        'category': categories['Desserts'],
                        'image': 'dishes/vanilla-ice-cream.jpg',
                        'ingredients': 'Milk, cream, vanilla, sugar',
                        'is_available': True,
                        'is_vegetarian': True,
                        'is_spicy': False,
                        'preparation_time': 2,
                        'stock_quantity': 100,
                    },

                    # Main Dishes
                    {
                        'name': 'Grilled Chicken',
                        'description': 'Perfectly grilled chicken breast with herbs',
                        'price': Decimal('16.99'),
                        'category': categories['Main Dishes'],
                        'image': 'dishes/grilled-chicken.jpg',
                        'ingredients': 'Chicken breast, herbs, olive oil, garlic',
                        'is_available': True,
                        'is_vegetarian': False,
                        'is_spicy': False,
                        'preparation_time': 25,
                        'stock_quantity': 35,
                    },
                    {
                        'name': 'Spaghetti Carbonara',
                        'description': 'Traditional Italian pasta with bacon and eggs',
                        'price': Decimal('14.99'),
                        'category': categories['Main Dishes'],
                        'image': 'dishes/spaghetti-carbonara.jpg',
                        'ingredients': 'Spaghetti, bacon, eggs, parmesan cheese, black pepper',
                        'is_available': True,
                        'is_vegetarian': False,
                        'is_spicy': False,
                        'preparation_time': 20,
                        'stock_quantity': 40,
                    },
                    {
                        'name': 'Fish and Chips',
                        'description': 'Crispy battered fish with golden fries',
                        'price': Decimal('13.99'),
                        'category': categories['Main Dishes'],
                        'image': 'dishes/fish-and-chips.jpg',
                        'ingredients': 'White fish, batter, potatoes, oil',
                        'is_available': True,
                        'is_vegetarian': False,
                        'is_spicy': False,
                        'preparation_time': 22,
                        'stock_quantity': 45,
                    },
                ]

                # Create dishes
                for dish_data in dishes_data:
                    dish = Dish.objects.create(**dish_data)
                    self.stdout.write(f'✅ Created dish: {dish.name} in {dish.category.name}')

                self.stdout.write(
                    self.style.SUCCESS(f'\n🎉 Successfully created {len(categories)} categories and {len(dishes_data)} dishes!')
                )
                self.stdout.write(
                    self.style.SUCCESS('All dishes have been configured with proper Cloudinary image paths.')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating data: {str(e)}')
            ) 