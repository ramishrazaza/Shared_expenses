from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from expenses.models import Group, GroupMembership
from datetime import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds initial users, groups, and membership history for the Spreetail assignment'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial data...')

        # 1. Create or get default Group
        group, created = Group.objects.get_or_create(
            name='Flatmates',
            defaults={'base_currency': 'INR'}
        )
        if created:
            self.stdout.write(f'Created group: {group.name}')
        else:
            self.stdout.write(f'Group: {group.name} already exists')

        # 2. Define users, their join/leave dates, and passwords
        users_data = [
            {'username': 'Aisha', 'email': 'aisha@example.com', 'joined_at': '2026-02-01', 'left_at': None},
            {'username': 'Rohan', 'email': 'rohan@example.com', 'joined_at': '2026-02-01', 'left_at': None},
            {'username': 'Priya', 'email': 'priya@example.com', 'joined_at': '2026-02-01', 'left_at': None},
            {'username': 'Meera', 'email': 'meera@example.com', 'joined_at': '2026-02-01', 'left_at': '2026-03-31'},
            {'username': 'Dev', 'email': 'dev@example.com', 'joined_at': '2026-02-08', 'left_at': None},
            {'username': 'Sam', 'email': 'sam@example.com', 'joined_at': '2026-04-08', 'left_at': None},
            {'username': 'Kabir', 'email': 'kabir@example.com', 'joined_at': '2026-03-11', 'left_at': '2026-03-12'}, # Dev's friend Kabir joined for Goa parasailing
        ]

        for u_info in users_data:
            # Create user
            username = u_info['username']
            email = u_info['email']
            user, u_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if u_created or not user.password:
                user.set_password('password123')
                user.save()
                self.stdout.write(f"Created user: {username} (password: 'password123')")
            else:
                self.stdout.write(f"User: {username} already exists")

            # Create or update membership
            joined = datetime.strptime(u_info['joined_at'], '%Y-%m-%d').date()
            left = datetime.strptime(u_info['left_at'], '%Y-%m-%d').date() if u_info['left_at'] else None
            is_active = (left is None)

            membership, m_created = GroupMembership.objects.get_or_create(
                group=group,
                user=user,
                defaults={
                    'joined_at': joined,
                    'left_at': left,
                    'is_active': is_active
                }
            )
            if not m_created:
                membership.joined_at = joined
                membership.left_at = left
                membership.is_active = is_active
                membership.save()
                self.stdout.write(f"Updated membership for {username}")
            else:
                self.stdout.write(f"Created membership for {username} (joined: {joined}, left: {left})")

        self.stdout.write(self.style.SUCCESS('Successfully seeded database!'))
