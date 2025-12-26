from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from admin_panel.models import SystemConfig

User = get_user_model()


class Command(BaseCommand):
    help = 'راه‌اندازی اولیه پنل ادمین'

    def handle(self, *args, **options):
        self.stdout.write('Setting up admin panel...')

        # ایجاد تنظیمات پیش‌فرض سیستم
        default_configs = [
            {
                'key': 'site_name',
                'value': 'BitTorrent Tracker',
                'config_type': 'global',
                'description': 'نام سایت'
            },
            {
                'key': 'max_users_per_ip',
                'value': '5',
                'config_type': 'security',
                'description': 'حداکثر تعداد کاربران از یک IP'
            },
            {
                'key': 'invite_required',
                'value': 'true',
                'config_type': 'global',
                'description': 'نیاز به کد دعوت برای ثبت‌نام'
            },
            {
                'key': 'announce_interval',
                'value': '1800',
                'config_type': 'tracker',
                'description': 'فاصله announce به ثانیه'
            },
            {
                'key': 'max_torrent_size_gb',
                'value': '100',
                'config_type': 'torrent',
                'description': 'حداکثر اندازه تورنت به GB'
            },
            {
                'key': 'credit_multiplier',
                'value': '1.0',
                'config_type': 'credit',
                'description': 'ضریب credit آپلود'
            },
            {
                'key': 'auto_ban_ratio_threshold',
                'value': '0.1',
                'config_type': 'security',
                'description': 'حداقل ratio قبل از مسدودی خودکار'
            },
            {
                'key': 'maintenance_mode',
                'value': 'false',
                'config_type': 'system',
                'description': 'حالت نگهداری سیستم'
            }
        ]

        created_count = 0
        for config_data in default_configs:
            config, created = SystemConfig.objects.get_or_create(
                key=config_data['key'],
                defaults=config_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created config: {config.key}')

        # ارتقای کاربر admin به staff اگر وجود داشته باشد
        try:
            admin_user = User.objects.get(username='admin')
            if not admin_user.is_staff:
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()
                self.stdout.write('  Promoted admin user to staff/superuser')
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  Admin user not found. Create it first with createsuperuser')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} system configurations')
        )
