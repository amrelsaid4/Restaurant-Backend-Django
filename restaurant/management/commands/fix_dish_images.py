from django.core.management.base import BaseCommand
from restaurant.models import Dish
import os


class Command(BaseCommand):
    help = 'Fix existing dish images to use proper Cloudinary URLs'

    def handle(self, *args, **options):
        # Correctly filter for local paths, excluding Cloudinary URLs
        dishes_with_old_paths = Dish.objects.exclude(image__startswith='http').exclude(image__exact='')
        
        updated_count = 0
        for dish in dishes_with_old_paths:
            old_image_path = str(dish.image)
            
            # Extract just the filename from the path
            if 'dishes/' in old_image_path:
                filename = old_image_path.split('dishes/')[-1]
            else:
                filename = os.path.basename(old_image_path)
            
            # Remove any versioning part from filename if present
            # Example: image_v12345.jpg -> image.jpg
            if '/upload/' in filename:
                filename = filename.split('/')[-1]

            # Reconstruct a simple path for Cloudinary
            new_image_path = f"dishes/{filename}"

            dish.image.name = new_image_path
            dish.save(update_fields=['image'])
            
            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Updated {dish.name}: old path was "{old_image_path}"')
            )
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully queued {updated_count} dish images for re-upload to Cloudinary.')
            )
            self.stdout.write(
                self.style.WARNING(f'The images will now be served from Cloudinary. Please verify on your website.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All dish images are already using Cloudinary URLs. No changes needed.')
            ) 