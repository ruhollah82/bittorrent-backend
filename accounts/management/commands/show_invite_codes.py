from django.core.management.base import BaseCommand
from django.db import models
from accounts.models import InviteCode
from django.utils import timezone


class Command(BaseCommand):
    help = 'نمایش کدهای دعوت موجود'

    def add_arguments(self, parser):
        parser.add_argument(
            '--first-only',
            action='store_true',
            help='نمایش تنها اولین کد دعوت موجود',
        )

    def handle(self, *args, **options):
        if options['first_only']:
            # Get first unused invite code
            invite_code = InviteCode.objects.filter(
                is_active=True,
                used_by__isnull=True,
                expires_at__isnull=True
            ).first() or InviteCode.objects.filter(
                is_active=True,
                used_by__isnull=True,
                expires_at__gt=timezone.now()
            ).first()

            if invite_code:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'🎫 First available invite code: {invite_code.code}'
                    )
                )
                self.stdout.write(f'📅 Expires: {invite_code.expires_at or "Never"}')
                self.stdout.write(f'✅ Active: {invite_code.is_active}')
            else:
                self.stdout.write(
                    self.style.WARNING('❌ No available invite codes found')
                )
                self.stdout.write(
                    self.style.INFO('💡 Create some: python manage.py create_invite --count 5 --expires 30')
                )
        else:
            # Show all invite codes
            total_codes = InviteCode.objects.count()
            active_codes = InviteCode.objects.filter(is_active=True).count()
            used_codes = InviteCode.objects.filter(used_by__isnull=False).count()
            available_codes = InviteCode.objects.filter(
                is_active=True,
                used_by__isnull=True,
                expires_at__isnull=True
            ).count() + InviteCode.objects.filter(
                is_active=True,
                used_by__isnull=True,
                expires_at__gt=timezone.now()
            ).count()

            self.stdout.write(f'📊 Invite Codes Summary:')
            self.stdout.write(f'   Total: {total_codes}')
            self.stdout.write(f'   Active: {active_codes}')
            self.stdout.write(f'   Used: {used_codes}')
            self.stdout.write(f'   Available: {available_codes}')

            if available_codes > 0:
                self.stdout.write(self.style.SUCCESS(f'\n🎫 Available Codes:'))
                codes = InviteCode.objects.filter(
                    is_active=True,
                    used_by__isnull=True
                ).filter(
                    models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
                ).order_by('created_at')[:10]  # Show first 10

                for code in codes:
                    expiry = code.expires_at.strftime('%Y-%m-%d') if code.expires_at else 'Never'
                    self.stdout.write(f'   {code.code} (expires: {expiry})')
