from django.core.management.base import BaseCommand
from torrents.models import Torrent
from accounts.models import User

class Command(BaseCommand):
    help = 'ایجاد تورنت نمونه برای تست'

    def handle(self, *args, **options):
        # دریافت کاربر ادمین
        try:
            admin = User.objects.get(username='admin')
        except User.DoesNotExist:
            self.stderr.write('کاربر admin یافت نشد.')
            return

        # ایجاد تورنت نمونه
        torrent = Torrent.objects.create(
            info_hash='aabbccddeeff00112233445566778899aabbccdd',  # 40 کاراکتر hex
            name='Test Torrent',
            description='تورنت آزمایشی برای تست سیستم',
            size=1024 * 1024 * 100,  # 100 MB
            created_by=admin
        )

        self.stdout.write(
            self.style.SUCCESS(f'تورنت نمونه ایجاد شد: {torrent.name}')
        )
        self.stdout.write(f'Info Hash: {torrent.info_hash}')
        self.stdout.write(f'Size: {torrent.size_gb} GB')
