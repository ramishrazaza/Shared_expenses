from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, date
from expenses.models import Group, GroupMembership, Expense, ExpenseParticipant, Settlement, ImportBatch, ImportAnomaly
from expenses.services.balance_service import BalanceService
from expenses.services.import_service import CSVImportService

User = get_user_model()

class ExpenseModelTests(TestCase):
    def setUp(self):
        # Create test users
        self.aisha = User.objects.create_user(username='Aisha', password='password123')
        self.rohan = User.objects.create_user(username='Rohan', password='password123')
        self.priya = User.objects.create_user(username='Priya', password='password123')
        self.meera = User.objects.create_user(username='Meera', password='password123')
        
        # Create test group
        self.group = Group.objects.create(name='Flatmates', base_currency='INR')
        
        # Add memberships
        GroupMembership.objects.create(group=self.group, user=self.aisha, joined_at=date(2026, 2, 1))
        GroupMembership.objects.create(group=self.group, user=self.rohan, joined_at=date(2026, 2, 1))
        GroupMembership.objects.create(group=self.group, user=self.priya, joined_at=date(2026, 2, 1))
        GroupMembership.objects.create(group=self.group, user=self.meera, joined_at=date(2026, 2, 1), left_at=date(2026, 3, 31))

    def test_equal_split_calculation(self):
        """
        Verify equal split calculation and remainder adjustment.
        10 INR split equally among Aisha, Rohan, Priya (3 people).
        Expected: 3.34, 3.33, 3.33 (First person receives the 1 paisa adjustment).
        """
        participants = ['Aisha', 'Rohan', 'Priya']
        splits = BalanceService.calculate_splits(
            total_amount=Decimal('10.00'),
            split_type='equal',
            participants_usernames=participants,
            payer_username='Aisha'
        )
        
        self.assertEqual(len(splits), 3)
        self.assertEqual(splits['Aisha'][0], Decimal('3.34'))
        self.assertEqual(splits['Rohan'][0], Decimal('3.33'))
        self.assertEqual(splits['Priya'][0], Decimal('3.33'))
        
        # Verify sum matches total
        total_shares = sum(item[0] for item in splits.values())
        self.assertEqual(total_shares, Decimal('10.00'))

    def test_percentage_split_calculation(self):
        """
        Verify percentage split calculation.
        """
        participants = ['Aisha', 'Rohan', 'Priya', 'Meera']
        split_details = "Aisha 30%; Rohan 30%; Priya 30%; Meera 10%"
        splits = BalanceService.calculate_splits(
            total_amount=Decimal('1000.00'),
            split_type='percentage',
            participants_usernames=participants,
            split_details_str=split_details
        )
        
        self.assertEqual(splits['Aisha'][0], Decimal('300.00'))
        self.assertEqual(splits['Rohan'][0], Decimal('300.00'))
        self.assertEqual(splits['Priya'][0], Decimal('300.00'))
        self.assertEqual(splits['Meera'][0], Decimal('100.00'))

    def test_share_split_calculation(self):
        """
        Verify share-based split calculation (e.g. Scooter rentals).
        Total 3600. Aisha: 1 share, Rohan: 2 shares, Priya: 1 share, Dev: 2 shares. Total shares = 6.
        Expected: Aisha: 600, Rohan: 1200, Priya: 600, Dev: 1200.
        """
        participants = ['Aisha', 'Rohan', 'Priya', 'Dev']
        split_details = "Aisha 1; Rohan 2; Priya 1; Dev 2"
        splits = BalanceService.calculate_splits(
            total_amount=Decimal('3600.00'),
            split_type='share',
            participants_usernames=participants,
            split_details_str=split_details
        )
        
        self.assertEqual(splits['Aisha'][0], Decimal('600.00'))
        self.assertEqual(splits['Rohan'][0], Decimal('1200.00'))
        self.assertEqual(splits['Priya'][0], Decimal('600.00'))
        self.assertEqual(splits['Dev'][0], Decimal('1200.00'))

    def test_simplified_debts(self):
        """
        Verify simplified balances flow.
        Suppose:
        - Aisha paid 1200. Split equal: Aisha, Rohan, Priya. Net: Aisha gets +800, Rohan owes 400, Priya owes 400.
        - Rohan paid 1200. Split equal: Aisha, Rohan, Priya. Net: Rohan gets +800, Aisha owes 400, Priya owes 400.
        Overall:
        - Aisha balance: +800 - 400 = +400
        - Rohan balance: -400 + 800 = +400
        - Priya balance: -400 - 400 = -800
        Simplified: Priya pays Aisha 400, Priya pays Rohan 400.
        """
        # Create expenses
        e1 = Expense.objects.create(
            group=self.group, description="E1", paid_by=self.aisha,
            total_amount=Decimal('1200.00'), amount_in_base=Decimal('1200.00'),
            split_type='equal', date=date(2026, 2, 1)
        )
        for u in [self.aisha, self.rohan, self.priya]:
            ExpenseParticipant.objects.create(expense=e1, user=u, share_amount=Decimal('400.00'))

        e2 = Expense.objects.create(
            group=self.group, description="E2", paid_by=self.rohan,
            total_amount=Decimal('1200.00'), amount_in_base=Decimal('1200.00'),
            split_type='equal', date=date(2026, 2, 2)
        )
        for u in [self.aisha, self.rohan, self.priya]:
            ExpenseParticipant.objects.create(expense=e2, user=u, share_amount=Decimal('400.00'))

        net_balances = BalanceService.get_group_net_balances(self.group.id)
        self.assertEqual(net_balances['Aisha'], Decimal('400.00'))
        self.assertEqual(net_balances['Rohan'], Decimal('400.00'))
        self.assertEqual(net_balances['Priya'], Decimal('-800.00'))

        debts = BalanceService.get_simplified_debts(self.group.id)
        self.assertEqual(len(debts), 2)
        
        # Verify Priya is the debtor paying Aisha and Rohan
        for debt in debts:
            self.assertEqual(debt['from_user'], 'Priya')
            self.assertEqual(debt['amount'], Decimal('400.00'))
            self.assertIn(debt['to_user'], ['Aisha', 'Rohan'])

    def test_csv_anomaly_detection_dry_run(self):
        """
        Test that process_dry_run flags anomalies correctly.
        """
        csv_data = (
            "date,description,paid_by,amount,currency,split_type,split_with,split_details,notes\n"
            "2026-02-01,Rent,Aisha,48000,INR,equal,\"Aisha;Rohan;Priya;Meera\",,\n" # Valid
            "2026-02-08,Dinner,Dev,3200,INR,equal,\"Aisha;Rohan;Priya;Dev\",,\n" # Duplicate Row 1
            "2026-02-08,dinner - marina bites,Dev,3200,INR,equal,\"Aisha;Rohan;Priya;Dev\",,\n" # Duplicate Row 2
            "2026-02-10,Electricity,Aisha,\"1,200\",INR,equal,\"Aisha;Rohan;Priya;Meera\",,\n" # Quotes and commas
            "2026-04-02,Groceries,Priya,2640,INR,equal,\"Aisha;Rohan;Priya;Meera\",,\n" # Membership conflict (Meera left Mar 31)
        )
        
        batch = CSVImportService.process_dry_run(self.group.id, csv_data, "test.csv", self.aisha)
        
        # Verify ImportAnomaly records
        anomalies = ImportAnomaly.objects.filter(batch=batch)
        anomaly_types = [an.anomaly_type for an in anomalies]
        
        self.assertIn('format_issue', anomaly_types)
        self.assertIn('duplicate_record', anomaly_types)
        self.assertIn('membership_conflict', anomaly_types)
