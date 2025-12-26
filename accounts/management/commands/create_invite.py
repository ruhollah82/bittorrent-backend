from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import InviteCode, User


class Command(BaseCommand):
    help = 'ایجاد کد دعوت جدید'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='تعداد کدهای دعوت برای ایجاد',
        )
        parser.add_argument(
            '--expires',
            type=int,
            default=30,
            help='زمان انقضا به روز',
        )
        parser.add_argument(
            '--created-by',
            type=str,
            help='نام کاربری ایجاد کننده',
        )

    def handle(self, *args, **options):
        count = options['count']
        expires_days = options['expires']
        created_by_username = options['created_by']

        created_by = None
        if created_by_username:
            try:
                created_by = User.objects.get(username=created_by_username)
            except User.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f'کاربر {created_by_username} یافت نشد.')
                )
                return

        expires_at = None
        if expires_days > 0:
            expires_at = timezone.now() + timedelta(days=expires_days)

        codes = []
        for i in range(count):
            invite = InviteCode.objects.create(
                created_by=created_by,
                expires_at=expires_at
            )
            codes.append(invite.code)

        self.stdout.write(
            self.style.SUCCESS(
                f'{count} کد دعوت ایجاد شد:'
            )
        )
        for code in codes:
            self.stdout.write(f'  {code}')

        if expires_at:
            self.stdout.write(
                self.style.WARNING(
                    f'کدهای دعوت تا {expires_at.date()} معتبر هستند.'
                )
            )
