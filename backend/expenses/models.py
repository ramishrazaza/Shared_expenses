import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom User model extending AbstractUser to keep auth clean and scalable.
    """
    id = models.AutoField(primary_key=True)
    
    def __str__(self):
        return self.username

class Group(models.Model):
    """
    Represents an expense group (e.g., 'Flatmates' or 'Goa Trip').
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    base_currency = models.CharField(max_length=10, default='INR')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    """
    Tracks dynamic group memberships over time, including join and leave dates.
    This model allows user membership to change, which handles the case of
    Meera moving out and Sam moving in.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('group', 'user')
        indexes = [
            models.Index(fields=['group', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

class Expense(models.Model):
    """
    Stores individual expenses. Supports soft delete.
    """
    SPLIT_CHOICES = [
        ('equal', 'Equal'),
        ('unequal', 'Unequal'),
        ('percentage', 'Percentage'),
        ('share', 'Share'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_expenses')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    exchange_rate = models.DecimalField(max_digits=8, decimal_places=4, default=1.0)
    amount_in_base = models.DecimalField(max_digits=12, decimal_places=2)
    split_type = models.CharField(max_length=20, choices=SPLIT_CHOICES, default='equal')
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.description} ({self.total_amount} {self.currency})"

class ExpenseParticipant(models.Model):
    """
    Links users to expenses they are a part of, specifying their share amount.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_shares')
    share_amount = models.DecimalField(max_digits=12, decimal_places=2)
    raw_share_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # stores %, shares, or direct amount
    is_settled = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('expense', 'user')
        indexes = [
            models.Index(fields=['expense', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} owes {self.share_amount} for {self.expense.description}"

class Settlement(models.Model):
    """
    Records direct debt settlements between two members (e.g., Rohan paid Aisha back).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_settlements')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    exchange_rate = models.DecimalField(max_digits=8, decimal_places=4, default=1.0)
    amount_in_base = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username}: {self.amount} {self.currency}"

class ImportBatch(models.Model):
    """
    Tracks CSV imports.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    csv_data = models.TextField(null=True, blank=True) # stores the original raw CSV content
    status = models.CharField(max_length=20, default='pending_review') # pending_review, completed, failed
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='import_batches')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.file_name} ({self.status})"

class ImportAnomaly(models.Model):
    """
    Logs anomalies detected in the CSV import process.
    """
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('detected', 'Detected'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='anomalies')
    row_number = models.IntegerField()
    raw_row_data = models.JSONField()
    anomaly_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    suggested_action = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='detected')
    resolved_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Row {row_number} [{anomaly_type}] - {severity}"

class AuditLog(models.Model):
    """
    Maintains an audit log for corrections and balance explanations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50) # create, update, delete, resolve_anomaly
    table_name = models.CharField(max_length=50)
    record_id = models.UUIDField(null=True, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.table_name} at {self.timestamp}"
