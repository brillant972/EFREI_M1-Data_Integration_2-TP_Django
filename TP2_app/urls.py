from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

router = DefaultRouter()
router.register(r'resource-access', views.ResourceAccessViewSet)
router.register(r'transactions', views.TransactionViewSet)

urlpatterns = [
    # Endpoints d'authentification
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('', include(router.urls)),
    
    # Partie I - Gestion des droits (endpoints supplémentaires)
    path('grant-access/', views.ResourceAccessViewSet.as_view({'post': 'grant_access'}), name='grant_access'),
    path('revoke-access/', views.ResourceAccessViewSet.as_view({'post': 'revoke_access'}), name='revoke_access'),
    
    # Partie II - Récupération des données
    path('file-data/<path:file_path>/', views.file_data, name='file_data'),
    
    # Partie III - Métriques
    path('metrics/recent-spending/', views.recent_spending, name='recent_spending'),
    path('metrics/user-spending/', views.user_spending_by_payment, name='user_spending'),
    path('metrics/top-products/', views.top_products, name='top_products'),
    
    # Partie IV - Lignage des données, audit et logs
    path('data-version/<int:resource_id>/<int:version>/', views.get_data_version, name='get_data_version'),
    path('access-logs/<int:resource_id>/', views.access_logs, name='access_logs'),
    path('resources/', views.list_resources, name='list_resources'),
    
    # Partie V - Fonctionnalités avancées
    path('search/', views.full_text_search, name='full_text_search'),
    path('ml/train/', views.train_ml_model, name='train_ml_model'),
    path('repush-transaction/<str:transaction_id>/', views.repush_transaction, name='repush_transaction'),
    path('repush-all/', views.repush_all_transactions, name='repush_all_transactions'),
]