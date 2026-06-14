from rest_framework import serializers
from django.contrib.auth import get_user_model
from expenses.models import (
    Group, GroupMembership, Expense, ExpenseParticipant,
    Settlement, ImportBatch, ImportAnomaly, AuditLog
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'base_currency', 'created_at')

class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = GroupMembership
        fields = ('id', 'user', 'user_id', 'joined_at', 'left_at', 'is_active')

class ExpenseParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = ExpenseParticipant
        fields = ('id', 'user', 'user_id', 'share_amount', 'raw_share_value', 'is_settled')

class ExpenseSerializer(serializers.ModelSerializer):
    paid_by = UserSerializer(read_only=True)
    paid_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='paid_by', write_only=True
    )
    participants = ExpenseParticipantSerializer(many=True, read_only=True)
    participants_input = serializers.ListField(
        child=serializers.JSONField(), write_only=True, required=False
    )

    class Meta:
        model = Expense
        fields = (
            'id', 'group', 'description', 'paid_by', 'paid_by_id',
            'total_amount', 'currency', 'exchange_rate', 'amount_in_base',
            'split_type', 'date', 'created_at', 'updated_at', 'is_deleted',
            'participants', 'participants_input'
        )
        read_only_fields = ('amount_in_base',)

    def create(self, validated_data):
        participants_data = validated_data.pop('participants_input', [])
        # Set amount in base currency
        exchange_rate = validated_data.get('exchange_rate', 1.0)
        total_amount = validated_data.get('total_amount')
        validated_data['amount_in_base'] = total_amount * exchange_rate

        expense = Expense.objects.create(**validated_data)

        # Create participants
        for p_data in participants_data:
            user_id = p_data.get('user_id')
            share_amount = p_data.get('share_amount')
            raw_share_value = p_data.get('raw_share_value')
            user_inst = User.objects.get(id=user_id)
            ExpenseParticipant.objects.create(
                expense=expense,
                user=user_inst,
                share_amount=share_amount,
                raw_share_value=raw_share_value
            )
        return expense

class SettlementSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    from_user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='from_user', write_only=True
    )
    to_user = UserSerializer(read_only=True)
    to_user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='to_user', write_only=True
    )

    class Meta:
        model = Settlement
        fields = (
            'id', 'group', 'from_user', 'from_user_id', 'to_user', 'to_user_id',
            'amount', 'currency', 'exchange_rate', 'amount_in_base', 'date', 'created_at'
        )
        read_only_fields = ('amount_in_base',)

    def create(self, validated_data):
        exchange_rate = validated_data.get('exchange_rate', 1.0)
        amount = validated_data.get('amount')
        validated_data['amount_in_base'] = amount * exchange_rate
        return Settlement.objects.create(**validated_data)

class ImportBatchSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    anomalies_count = serializers.SerializerMethodField()

    class Meta:
        model = ImportBatch
        fields = ('id', 'file_name', 'status', 'created_by', 'created_at', 'anomalies_count')

    def get_anomalies_count(self, obj):
        return obj.anomalies.count()

class ImportAnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportAnomaly
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'
