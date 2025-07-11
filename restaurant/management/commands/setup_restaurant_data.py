from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction


class Command(BaseCommand):
    help = 'Complete restaurant data setup: clear old data, upload images, and populate fresh data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all existing data and complete setup',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR('⚠️  WARNING: This will completely reset your restaurant data!')
            )
            self.stdout.write(
                self.style.WARNING('This will:')
            )
            self.stdout.write('  • Delete ALL existing dishes and categories')
            self.stdout.write('  • Upload new sample images to Cloudinary')
            self.stdout.write('  • Create fresh dishes and categories with proper images')
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('Run with --confirm to proceed: python manage.py setup_restaurant_data --confirm')
            )
            return

        try:
            self.stdout.write(
                self.style.SUCCESS('🚀 Starting complete restaurant data setup...\n')
            )

            # Step 1: Clear all existing data
            self.stdout.write('📋 Step 1: Clearing existing data...')
            call_command('clear_all_data', '--confirm')
            self.stdout.write(self.style.SUCCESS('✅ Data cleared successfully!\n'))

            # Step 2: Upload sample images to Cloudinary
            self.stdout.write('📋 Step 2: Uploading sample images to Cloudinary...')
            call_command('upload_sample_images')
            self.stdout.write(self.style.SUCCESS('✅ Images uploaded successfully!\n'))

            # Step 3: Populate fresh data
            self.stdout.write('📋 Step 3: Creating fresh dishes and categories...')
            call_command('populate_fresh_data')
            self.stdout.write(self.style.SUCCESS('✅ Fresh data created successfully!\n'))

            self.stdout.write(
                self.style.SUCCESS('🎉 COMPLETE! Restaurant data setup finished successfully!')
            )
            self.stdout.write(
                self.style.SUCCESS('Your restaurant now has fresh dishes and categories with proper Cloudinary images.')
            )
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('📝 Next steps:')
            )
            self.stdout.write('  1. Test creating new dishes through the admin panel')
            self.stdout.write('  2. Test editing existing dishes')
            self.stdout.write('  3. Test deleting dishes')
            self.stdout.write('  4. Verify all changes persist after page reload')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Setup failed: {str(e)}')
            )
            self.stdout.write(
                self.style.ERROR('Please check the error above and try again.')
            ) 