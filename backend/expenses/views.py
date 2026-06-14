import csv
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.views import TokenObtainPairView
from expenses.models import (
    Group, GroupMembership, Expense, ExpenseParticipant,
    Settlement, ImportBatch, ImportAnomaly, AuditLog
)
from expenses.serializers import (
    UserSerializer, GroupSerializer, GroupMembershipSerializer,
    ExpenseSerializer, SettlementSerializer, ImportBatchSerializer,
    ImportAnomalySerializer, AuditLogSerializer
)
from expenses.services.import_service import CSVImportService
from expenses.services.balance_service import BalanceService

User = get_user_model()

class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username is already taken.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(username=username, password=password, email=email)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        group = self.get_object()
        memberships = GroupMembership.objects.filter(group=group)
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get('user_id')
        joined_at = request.data.get('joined_at')

        if not user_id or not joined_at:
            return Response(
                {'error': 'user_id and joined_at date are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        membership, created = GroupMembership.objects.get_or_create(
            group=group,
            user=user,
            defaults={'joined_at': joined_at, 'is_active': True}
        )

        if not created:
            membership.joined_at = joined_at
            membership.left_at = None
            membership.is_active = True
            membership.save()

        # Log change
        AuditLog.objects.create(
            user=request.user,
            action='member_join',
            table_name='GroupMembership',
            record_id=membership.id,
            new_value={'user': user.username, 'joined_at': joined_at}
        )

        return Response(GroupMembershipSerializer(membership).data)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get('user_id')
        left_at = request.data.get('left_at')

        if not user_id or not left_at:
            return Response(
                {'error': 'user_id and left_at date are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        membership = get_object_or_404(GroupMembership, group=group, user=user)
        
        old_val = {'left_at': str(membership.left_at), 'is_active': membership.is_active}
        
        membership.left_at = left_at
        membership.is_active = False
        membership.save()

        # Log change
        AuditLog.objects.create(
            user=request.user,
            action='member_leave',
            table_name='GroupMembership',
            record_id=membership.id,
            old_value=old_val,
            new_value={'left_at': left_at, 'is_active': False}
        )

        return Response(GroupMembershipSerializer(membership).data)

    @action(detail=True, methods=['get'])
    def balances(self, request, pk=None):
        group = self.get_object()
        net_balances = BalanceService.get_group_net_balances(group.id)
        simplified_debts = BalanceService.get_simplified_debts(group.id)
        
        return Response({
            'group_id': group.id,
            'net_balances': net_balances,
            'simplified_debts': simplified_debts
        })

    @action(detail=True, methods=['get'])
    def explain_balance(self, request, pk=None):
        group = self.get_object()
        username = request.query_params.get('username')
        if not username:
            return Response(
                {'error': 'username parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        trace = BalanceService.get_user_balance_trace(group.id, username)
        if 'error' in trace:
            return Response(trace, status=status.HTTP_400_BAD_REQUEST)
        return Response(trace)

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.filter(is_deleted=False).order_by('-date')
    serializer_class = ExpenseSerializer

    def perform_destroy(self, instance):
        # Implement soft delete
        instance.is_deleted = True
        instance.save()
        
        # Log deletion
        AuditLog.objects.create(
            user=self.request.user,
            action='delete',
            table_name='Expense',
            record_id=instance.id,
            old_value={'description': instance.description, 'total_amount': str(instance.total_amount)}
        )

class SettlementViewSet(viewsets.ModelViewSet):
    queryset = Settlement.objects.all().order_by('-date')
    serializer_class = SettlementSerializer

    def perform_create(self, serializer):
        settlement = serializer.save()
        # Log creation
        AuditLog.objects.create(
            user=self.request.user,
            action='create',
            table_name='Settlement',
            record_id=settlement.id,
            new_value={
                'from_user': settlement.from_user.username,
                'to_user': settlement.to_user.username,
                'amount': str(settlement.amount)
            }
        )

class ImportViewSet(viewsets.ModelViewSet):
    queryset = ImportBatch.objects.all().order_by('-created_at')
    serializer_class = ImportBatchSerializer

    @action(detail=False, methods=['post'])
    def upload_csv(self, request):
        file_obj = request.FILES.get('file')
        group_id = request.data.get('group_id')
        
        if not file_obj or not group_id:
            return Response(
                {'error': 'Both file and group_id are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        file_content = file_obj.read().decode('utf-8')
        batch = CSVImportService.process_dry_run(
            group_id=group_id,
            file_content=file_content,
            file_name=file_obj.name,
            user=request.user
        )
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def anomalies(self, request, pk=None):
        batch = self.get_object()
        anomalies = ImportAnomaly.objects.filter(batch=batch).order_by('row_number')
        return Response(ImportAnomalySerializer(anomalies, many=True).data)

    @action(detail=True, methods=['post'])
    def resolve_anomaly(self, request, pk=None):
        batch = self.get_object()
        anomaly_id = request.data.get('anomaly_id')
        action_type = request.data.get('status') # 'resolved', 'ignored'
        resolved_data = request.data.get('resolved_data') # overrides dict

        if not anomaly_id or not action_type:
            return Response(
                {'error': 'anomaly_id and status (resolved/ignored) are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        anomaly = get_object_or_404(ImportAnomaly, id=anomaly_id, batch=batch)
        anomaly.status = action_type
        if action_type == 'resolved' and resolved_data:
            anomaly.resolved_data = resolved_data
        anomaly.save()

        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='resolve_anomaly',
            table_name='ImportAnomaly',
            record_id=anomaly.id,
            new_value={'status': action_type, 'resolved_data': resolved_data}
        )

        return Response(ImportAnomalySerializer(anomaly).data)

    @action(detail=True, methods=['post'])
    def commit(self, request, pk=None):
        batch = self.get_object()
        if batch.status == 'completed':
            return Response({'error': 'Batch already committed.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stats = CSVImportService.commit_batch(batch.id, request.user)
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
