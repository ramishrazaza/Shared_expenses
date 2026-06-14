from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from expenses.views import (
    GroupViewSet, ExpenseViewSet, SettlementViewSet,
    ImportViewSet, AuditLogViewSet, RegisterViewSet
)

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'settlements', SettlementViewSet, basename='settlement')
router.register(r'imports', ImportViewSet, basename='import')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    # Router paths
    path('', include(router.urls)),
    
    # Registration & Auth
    path('auth/register/', RegisterViewSet.as_view({'post': 'create'}), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
