import os
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from restaurant.models import Category, Dish
from django.core.files import File
import shutil

def create_categories_and_dishes():
    # Define categories with English names
    categories_data = {
        'Pizza': 'Delicious pizzas made with fresh dough and finest ingredients',
        'Burgers': 'Tasty burgers with premium quality meats',
        'Pasta': 'Authentic Italian pasta with various sauces',
        'Salad': 'Fresh and healthy salads',
        'Drinks': 'Refreshing beverages and natural juices',
        'Desserts': 'Delicious and tasty desserts',
        'Appetizers': 'Delightful appetizers to start your meal'
    }
    
    # Create categories
    categories = {}
    for cat_name, description in categories_data.items():
        category, created = Category.objects.get_or_create(
            name=cat_name,
            defaults={'description': description}
        )
        categories[cat_name] = category
        print(f"Category '{cat_name}' {'created' if created else 'exists'}")
    
    # Define dishes with their correct image names
    dishes_data = {
        'Pizza': [
            {'name': 'Margherita Pizza', 'price': 85.00, 'image': 'Margherita Pizza.jpeg', 'description': 'Classic pizza with tomatoes, mozzarella, and fresh basil'},
            {'name': 'Pepperoni Pizza', 'price': 95.00, 'image': 'Pepperoni Pizza.jpeg', 'description': 'Delicious pizza with pepperoni slices and cheese'},
            {'name': 'BBQ Chicken Pizza', 'price': 110.00, 'image': 'BBQ Chicken Pizza.jpeg', 'description': 'Pizza with chicken and barbecue sauce'},
        ],
        'Burgers': [
            {'name': 'Bacon Burger', 'price': 120.00, 'image': 'Bacon Burger.jpeg', 'description': 'Delicious burger with crispy bacon and cheese'},
            {'name': 'Veggie Burger', 'price': 90.00, 'image': 'Veggie Burger.jpeg', 'description': 'Healthy and delicious vegetarian burger'},
            {'name': 'Classic Cheeseburger', 'price': 100.00, 'image': 'Classic Cheeseburger.jpeg', 'description': 'Classic burger with cheddar cheese'},
        ],
        'Pasta': [
            {'name': 'Penne Arrabbiata', 'price': 75.00, 'image': 'Penne Arrabbiata.jpeg', 'description': 'Pasta with spicy tomato sauce and garlic'},
        ],
        'Salad': [
            {'name': 'Caesar Salad', 'price': 65.00, 'image': 'Caesar Salad.jpeg', 'description': 'Classic Caesar salad with lettuce and cheese'},
            {'name': 'Greek Salad', 'price': 70.00, 'image': 'Greek Salad.jpeg', 'description': 'Traditional Greek salad with feta cheese'},
        ],
        'Drinks': [
            {'name': 'Cola', 'price': 25.00, 'image': 'Cola.jpeg', 'description': 'Refreshing carbonated drink'},
            {'name': 'Mango Smoothie', 'price': 35.00, 'image': 'Mango Smoothie.jpeg', 'description': 'Fresh and natural mango juice'},
        ],
        'Desserts': [
            {'name': 'Tiramisu', 'price': 55.00, 'image': 'Tiramisu.jpeg', 'description': 'Famous Italian tiramisu dessert'},
            {'name': 'Chocolate Cake', 'price': 45.00, 'image': 'Chocolate Cake.jpeg', 'description': 'Rich and delicious chocolate cake'},
            {'name': 'Vanilla Ice Cream', 'price': 30.00, 'image': 'Vanilla Ice Cream.jpeg', 'description': 'Creamy and delicious vanilla ice cream'},
        ],
        'Appetizers': []
    }
    
    # Delete existing dishes to avoid duplicates
    Dish.objects.all().delete()
    print("Existing dishes deleted")
    
    # Create dishes
    for cat_name, dishes in dishes_data.items():
        category = categories[cat_name]
        for dish_data in dishes:
            dish = Dish.objects.create(
                name=dish_data['name'],
                category=category,
                description=dish_data.get('description', f'Delicious {dish_data["name"]} from {cat_name} category'),
                price=dish_data['price'],
                is_vegetarian='Veggie' in dish_data['name'] or cat_name == 'Salad',
                is_spicy='Spicy' in dish_data['name'] or 'Arrabbiata' in dish_data['name'],
                preparation_time=15 + (5 * len(dish_data['name'].split())),  # Dynamic prep time
                calories=300 + (dish_data['price'] * 2),  # Dynamic calories based on price
                ingredients=f"Fresh ingredients for {dish_data['name']}"
            )
            
            # Set image if exists
            if 'image' in dish_data:
                image_path = Path(f'media/dishes/{cat_name}/{dish_data["image"]}')
                if image_path.exists():
                    with open(image_path, 'rb') as img_file:
                        dish.image.save(
                            dish_data["image"],
                            File(img_file),
                            save=True
                        )
                    print(f"Image set for {dish.name}")
                else:
                    print(f"Image not found: {image_path}")
            
            print(f"Dish '{dish.name}' created with price ${dish.price}")

if __name__ == '__main__':
    create_categories_and_dishes()
    print("\n✅ Database populated successfully with English content and images!") 