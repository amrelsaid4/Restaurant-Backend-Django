from django.core.management.base import BaseCommand
import cloudinary
import cloudinary.uploader
import requests
from django.conf import settings
import io


class Command(BaseCommand):
    help = 'Upload sample dish images to Cloudinary'

    def handle(self, *args, **options):
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
            api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
            api_secret=settings.CLOUDINARY_STORAGE['API_SECRET']
        )

        # Sample food images URLs (high quality, royalty-free)
        sample_images = {
            'classic-cheeseburger': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
            'bacon-deluxe-burger': 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=800',
            'veggie-burger': 'https://images.unsplash.com/photo-1525059696034-4967a729002e?w=800',
            'orange-juice': 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=800',
            'mango-smoothie': 'https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=800',
            'cola': 'https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=800',
            'caesar-salad': 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=800',
            'greek-salad': 'https://images.unsplash.com/photo-1544376664-80b17f09d399?w=800',
            'chocolate-cake': 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800',
            'tiramisu': 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800',
            'vanilla-ice-cream': 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=800',
            'grilled-chicken': 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=800',
            'spaghetti-carbonara': 'https://images.unsplash.com/photo-1621996346565-e3dbc353d2e5?w=800',
            'fish-and-chips': 'https://images.unsplash.com/photo-1544943910-4c1dc482d8c0?w=800',
        }

        uploaded_count = 0
        for image_name, image_url in sample_images.items():
            try:
                self.stdout.write(f'📤 Uploading {image_name}...')
                
                # Download image from URL
                response = requests.get(image_url)
                if response.status_code == 200:
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        io.BytesIO(response.content),
                        public_id=f"dishes/{image_name}",
                        folder="dishes",
                        resource_type="image",
                        format="jpg",
                        quality="auto:good",
                        width=800,
                        height=600,
                        crop="fill",
                        gravity="center"
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Uploaded {image_name}: {result["secure_url"]}')
                    )
                    uploaded_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Failed to download {image_name} from {image_url}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error uploading {image_name}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Successfully uploaded {uploaded_count}/{len(sample_images)} images to Cloudinary!')
        )
        self.stdout.write(
            self.style.SUCCESS('Images are now available at: https://res.cloudinary.com/dwrmh5o8q/image/upload/dishes/')
        ) 