from django.core.management.base import BaseCommand
from django.utils.text import slugify
from torrents.models import Category


class Command(BaseCommand):
    help = 'Populate basic torrent categories'

    def handle(self, *args, **options):
        categories_data = [
            {
                'name': 'Movies',
                'description': 'Movies and films',
                'icon': 'fas fa-film',
                'color': '#e74c3c',
                'sort_order': 1
            },
            {
                'name': 'TV Shows',
                'description': 'Television series and shows',
                'icon': 'fas fa-tv',
                'color': '#3498db',
                'sort_order': 2
            },
            {
                'name': 'Music',
                'description': 'Music albums, singles, and audio files',
                'icon': 'fas fa-music',
                'color': '#9b59b6',
                'sort_order': 3
            },
            {
                'name': 'Games',
                'description': 'Video games and gaming content',
                'icon': 'fas fa-gamepad',
                'color': '#e67e22',
                'sort_order': 4
            },
            {
                'name': 'Software',
                'description': 'Software applications and programs',
                'icon': 'fas fa-cogs',
                'color': '#95a5a6',
                'sort_order': 5
            },
            {
                'name': 'Books',
                'description': 'E-books, audiobooks, and literature',
                'icon': 'fas fa-book',
                'color': '#f39c12',
                'sort_order': 6
            },
            {
                'name': 'Anime',
                'description': 'Anime series, movies, and related content',
                'icon': 'fas fa-eye',
                'color': '#1abc9c',
                'sort_order': 7
            },
            {
                'name': 'Documentaries',
                'description': 'Documentary films and educational content',
                'icon': 'fas fa-graduation-cap',
                'color': '#34495e',
                'sort_order': 8
            },
            {
                'name': 'Other',
                'description': 'Miscellaneous content',
                'icon': 'fas fa-folder',
                'color': '#7f8c8d',
                'sort_order': 99
            }
        ]

        created_count = 0
        updated_count = 0

        for category_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=slugify(category_data['name']),
                defaults=category_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                # Update existing category with new data
                for key, value in category_data.items():
                    setattr(category, key, value)
                category.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated category: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count + updated_count} categories '
                f'({created_count} created, {updated_count} updated)'
            )
        )
