from django.core.management.base import BaseCommand
from django.utils import timezone
from logging_monitoring.tasks import update_daily_stats


class Command(BaseCommand):
    help = 'بروزرسانی آمار روزانه سیستم'

    def handle(self, *args, **options):
        self.stdout.write('Updating daily statistics...')

        result = update_daily_stats()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated statistics: {result}')
        )
