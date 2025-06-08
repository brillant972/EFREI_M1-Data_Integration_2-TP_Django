from django.shortcuts import render
from rest_framework import status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User
from .models import ResourceAccess, APIRequestLog, Transaction, ProductPurchase, DataLakeResource
from .serializers import (
    ResourceAccessSerializer, APIRequestLogSerializer, 
    TransactionSerializer, ProductPurchaseSerializer, 
    DataLakeResourceSerializer, UserSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
import os
import json
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from datetime import datetime, timedelta
from django.db.models import Sum
import csv

# Vues pour la partie I: Authentification et autorisation

class ResourceAccessViewSet(viewsets.ModelViewSet):
    """
    API endpoint pour gérer les droits d'accès aux ressources
    """
    queryset = ResourceAccess.objects.all()
    serializer_class = ResourceAccessSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resource_type', 'resource_path', 'can_read', 'can_write']
    
    def get_queryset(self):
        # Les administrateurs peuvent voir tous les droits d'accès
        # Les utilisateurs normaux ne peuvent voir que leurs droits
        if self.request.user.is_staff:
            return ResourceAccess.objects.all()
        return ResourceAccess.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # L'utilisateur qui crée le droit d'accès est défini comme celui qui l'a accordé
        serializer.save(granted_by=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def grant_access(self, request):
        """
        Accorder des droits d'accès à un utilisateur pour une ressource
        """
        try:
            user_id = request.data.get('user_id')
            resource_type = request.data.get('resource_type')
            resource_path = request.data.get('resource_path')
            can_read = request.data.get('can_read', False)
            can_write = request.data.get('can_write', False)
            
            if not all([user_id, resource_type, resource_path]):
                return Response(
                    {"error": "User ID, resource type and resource path are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier si l'utilisateur existe
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": f"User with ID {user_id} does not exist"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Créer ou mettre à jour les droits d'accès
            access, created = ResourceAccess.objects.update_or_create(
                user=user,
                resource_type=resource_type,
                resource_path=resource_path,
                defaults={
                    'can_read': can_read,
                    'can_write': can_write,
                    'granted_by': request.user
                }
            )
            
            serializer = ResourceAccessSerializer(access)
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def revoke_access(self, request):
        """
        Révoquer les droits d'accès d'un utilisateur pour une ressource
        """
        try:
            user_id = request.data.get('user_id')
            resource_type = request.data.get('resource_type')
            resource_path = request.data.get('resource_path')
            
            if not all([user_id, resource_type, resource_path]):
                return Response(
                    {"error": "User ID, resource type and resource path are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier si le droit d'accès existe
            try:
                access = ResourceAccess.objects.get(
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_path=resource_path
                )
                access.delete()
                return Response(
                    {"message": f"Access rights for user {user_id} to {resource_type}:{resource_path} revoked successfully"}, 
                    status=status.HTTP_200_OK
                )
            except ResourceAccess.DoesNotExist:
                return Response(
                    {"error": "Access right not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Fonctions utilitaires pour vérifier les droits d'accès
def check_file_access(user, file_path, need_write=False):
    """Vérifie si un utilisateur a accès à un fichier"""
    if user.is_staff:  # Les admins ont toujours accès
        return True
        
    access = ResourceAccess.objects.filter(
        user=user,
        resource_type='FILE',
        resource_path=file_path
    ).first()
    
    if not access:
        return False
    
    if need_write:
        return access.can_write
    return access.can_read

def check_table_access(user, table_name, need_write=False):
    """Vérifie si un utilisateur a accès à une table"""
    if user.is_staff:  # Les admins ont toujours accès
        return True
        
    access = ResourceAccess.objects.filter(
        user=user,
        resource_type='TABLE',
        resource_path=table_name
    ).first()
    
    if not access:
        return False
    
    if need_write:
        return access.can_write
    return access.can_read

# Vues pour la partie II: Récupération des données

class StandardResultsSetPagination(PageNumberPagination):
    """Pagination standard avec 10 éléments par page"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint pour consulter les transactions
    """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'payment_method': ['exact'],
        'country': ['exact', 'icontains'],
        'status': ['exact'],
        'amount': ['exact', 'gt', 'lt'],
        'customer_rating': ['exact', 'gt', 'lt'],
        'timestamp': ['gt', 'lt'],
    }
    ordering_fields = ['amount', 'timestamp', 'customer_rating']
    
    def get_queryset(self):
        """
        Cette vue retourne la liste des transactions avec:
        - Pagination
        - Filtrage sur plusieurs champs
        - Projection (sélection des champs)
        """
        queryset = Transaction.objects.all()
        
        # Filtrage par catégorie de produit
        product_category = self.request.query_params.get('product_category')
        if product_category:
            queryset = queryset.filter(product_purchases__category=product_category).distinct()
        
        # Projection (sélection des champs)
        fields = self.request.query_params.get('fields')
        if fields:
            self.serializer_class.Meta.fields = fields.split(',')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        Liste les transactions avec support de la projection
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        # Support de la projection (sélection des champs)
        fields = request.query_params.get('fields')
        if fields:
            fields_list = fields.split(',')
            serializer = self.get_serializer(page, many=True, fields=fields_list)
        else:
            serializer = self.get_serializer(page, many=True)
        
        return self.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def file_data(request, file_path):
    """
    Récupère les données d'un fichier du data lake avec pagination
    """
    # Vérifier les droits d'accès
    if not check_file_access(request.user, file_path):
        return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Vérifier si le fichier existe
        full_path = os.path.join('/path/to/datalake', file_path)
        if not os.path.exists(full_path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Charger le fichier selon son type
        _, ext = os.path.splitext(file_path)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Projection
        fields = request.query_params.get('fields')
        field_list = fields.split(',') if fields else None
        
        if ext.lower() == '.json':
            with open(full_path, 'r') as f:
                data = json.load(f)
                
                # Filtrage
                data = filter_data(data, request.query_params)
                
                # Pagination
                total_items = len(data)
                paginated_data = data[start_idx:end_idx]
                
                # Projection
                if field_list:
                    projected_data = []
                    for item in paginated_data:
                        projected_item = {field: item.get(field) for field in field_list if field in item}
                        projected_data.append(projected_item)
                    paginated_data = projected_data
                
                response = {
                    'data': paginated_data,
                    'pagination': {
                        'total_items': total_items,
                        'total_pages': (total_items + page_size - 1) // page_size,
                        'current_page': page,
                        'page_size': page_size,
                    }
                }
                return Response(response)
                
        elif ext.lower() == '.csv':
            with open(full_path, 'r') as f:
                csv_reader = csv.DictReader(f)
                data = list(csv_reader)
                
                # Filtrage
                data = filter_data(data, request.query_params)
                
                # Pagination
                total_items = len(data)
                paginated_data = data[start_idx:end_idx]
                
                # Projection
                if field_list:
                    projected_data = []
                    for item in paginated_data:
                        projected_item = {field: item.get(field) for field in field_list if field in item}
                        projected_data.append(projected_item)
                    paginated_data = projected_data
                
                response = {
                    'data': paginated_data,
                    'pagination': {
                        'total_items': total_items,
                        'total_pages': (total_items + page_size - 1) // page_size,
                        'current_page': page,
                        'page_size': page_size,
                    }
                }
                return Response(response)
        else:
            return Response({"error": "Unsupported file format"}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def filter_data(data, query_params):
    """
    Filtre les données selon les paramètres de requête
    """
    filtered_data = data
    
    # Filtrage par méthode de paiement
    payment_method = query_params.get('payment_method')
    if payment_method:
        filtered_data = [item for item in filtered_data if item.get('payment_method') == payment_method]
    
    # Filtrage par pays
    country = query_params.get('country')
    if country:
        filtered_data = [item for item in filtered_data if item.get('country') == country]
    
    # Filtrage par catégorie de produit
    product_category = query_params.get('product_category')
    if product_category:
        filtered_data = [
            item for item in filtered_data 
            if any(product.get('category') == product_category for product in item.get('products', []))
        ]
    
    # Filtrage par statut
    status = query_params.get('status')
    if status:
        filtered_data = [item for item in filtered_data if item.get('status') == status]
    
    # Filtrage par montant
    amount_eq = query_params.get('amount')
    amount_gt = query_params.get('amount_gt')
    amount_lt = query_params.get('amount_lt')
    
    if amount_eq:
        filtered_data = [item for item in filtered_data if float(item.get('amount', 0)) == float(amount_eq)]
    if amount_gt:
        filtered_data = [item for item in filtered_data if float(item.get('amount', 0)) > float(amount_gt)]
    if amount_lt:
        filtered_data = [item for item in filtered_data if float(item.get('amount', 0)) < float(amount_lt)]
    
    # Filtrage par évaluation client
    rating_eq = query_params.get('customer_rating')
    rating_gt = query_params.get('customer_rating_gt')
    rating_lt = query_params.get('customer_rating_lt')
    
    if rating_eq:
        filtered_data = [item for item in filtered_data if int(item.get('customer_rating', 0)) == int(rating_eq)]
    if rating_gt:
        filtered_data = [item for item in filtered_data if int(item.get('customer_rating', 0)) > int(rating_gt)]
    if rating_lt:
        filtered_data = [item for item in filtered_data if int(item.get('customer_rating', 0)) < int(rating_lt)]
    
    return filtered_data

# Vues pour la partie III: Métriques

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_spending(request):
    """
    Récupère les dépenses des 5 dernières minutes
    """
    # Calculer la date limite (5 minutes auparavant)
    time_threshold = datetime.now() - timedelta(minutes=5)
    
    # Récupérer toutes les transactions des 5 dernières minutes
    recent_transactions = Transaction.objects.filter(timestamp__gte=time_threshold)
    
    # Calculer le montant total dépensé
    total_amount = recent_transactions.aggregate(total=Sum('amount'))['total'] or 0
    
    # Préparer la réponse
    response = {
        'total_spent_last_5_minutes': float(total_amount),
        'currency': 'USD',
        'transaction_count': recent_transactions.count(),
        'timestamp': datetime.now()
    }
    
    return Response(response)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_spending_by_payment(request):
    """
    Récupère le total dépensé par utilisateur et type de transaction
    """
    # Agréger les données par utilisateur et méthode de paiement
    result = Transaction.objects.values('user__username', 'payment_method').annotate(
        total_spent=Sum('amount')
    ).order_by('user__username', 'payment_method')
    
    # Formater les données pour la réponse
    formatted_result = []
    for item in result:
        formatted_result.append({
            'username': item['user__username'],
            'payment_method': item['payment_method'],
            'total_spent': float(item['total_spent']),
            'currency': 'USD'
        })
    
    return Response(formatted_result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_products(request):
    """
    Récupère les X produits les plus achetés
    """
    try:
        # Récupérer le paramètre X (nombre de produits à afficher)
        x = int(request.query_params.get('x', 5))
        if x <= 0:
            return Response(
                {"error": "Parameter 'x' must be a positive integer"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Agréger les données par produit
        top_products = ProductPurchase.objects.values(
            'product_id', 'product_name', 'category'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('price')
        ).order_by('-total_quantity')[:x]
        
        # Formater les données pour la réponse
        result = []
        for product in top_products:
            result.append({
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'category': product['category'],
                'total_quantity_sold': product['total_quantity'],
                'total_revenue': float(product['total_revenue']),
                'currency': 'USD'
            })
        
        return Response(result)
    
    except ValueError:
        return Response(
            {"error": "Parameter 'x' must be a valid integer"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

# Vues pour la partie IV: Lignage des données, audit et logs

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data_version(request, resource_id, version):
    """
    Récupère une version spécifique des données stockées
    """
    try:
        # Vérifier si la ressource existe
        try:
            resource = DataLakeResource.objects.get(pk=resource_id)
        except DataLakeResource.DoesNotExist:
            return Response({"error": "Resource not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier si la ressource supporte le versionnement
        if not resource.version_control:
            return Response(
                {"error": "This resource does not support versioning"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier les droits d'accès
        if resource.resource_type == 'FILE':
            if not check_file_access(request.user, resource.path):
                return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
        elif resource.resource_type == 'TABLE':
            if not check_table_access(request.user, resource.path):
                return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
        
        # Pour cet exemple, on suppose que les transactions sont versionnées
        if resource.resource_type == 'TABLE' and resource.path == 'transactions':
            # Récupérer les données de la version spécifiée
            transactions = Transaction.objects.filter(version=version)
            serializer = TransactionSerializer(transactions, many=True)
            return Response({
                'resource': resource.name,
                'version': version,
                'data': serializer.data
            })
        else:
            # Dans un cas réel, il faudrait implémenter la récupération des versions
            # pour d'autres types de ressources (fichiers, etc.)
            return Response(
                {"error": "Version retrieval not implemented for this resource type"}, 
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
            
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def access_logs(request, resource_id):
    """
    Récupère qui a accédé à une ressource spécifique
    """
    try:
        # Vérifier si la ressource existe
        try:
            resource = DataLakeResource.objects.get(pk=resource_id)
        except DataLakeResource.DoesNotExist:
            return Response({"error": "Resource not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier si l'utilisateur est administrateur
        if not request.user.is_staff:
            return Response({"error": "Only administrators can access logs"}, status=status.HTTP_403_FORBIDDEN)
        
        # Rechercher les logs d'accès pour cette ressource
        # Supposons que l'endpoint contient le nom de la ressource
        logs = APIRequestLog.objects.filter(endpoint__contains=resource.name)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        
        paginated_logs = paginator.paginate_queryset(logs, request)
        serializer = APIRequestLogSerializer(paginated_logs, many=True)
        
        return paginator.get_paginated_response(serializer.data)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_resources(request):
    """
    Liste toutes les ressources disponibles dans le data lake
    """
    # Vérifier si l'utilisateur est authentifié
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Récupérer toutes les ressources du data lake
    resources = DataLakeResource.objects.all()
    
    # Filtrer les ressources auxquelles l'utilisateur a accès
    if not request.user.is_staff:  # Les administrateurs voient tout
        accessible_resources = []
        for resource in resources:
            if resource.resource_type == 'FILE':
                if check_file_access(request.user, resource.path):
                    accessible_resources.append(resource)
            elif resource.resource_type == 'TABLE':
                if check_table_access(request.user, resource.path):
                    accessible_resources.append(resource)
            else:
                # Pour les autres types de ressources, vérifier l'accès
                access = ResourceAccess.objects.filter(
                    user=request.user,
                    resource_type=resource.resource_type,
                    resource_path=resource.path,
                    can_read=True
                ).exists()
                if access:
                    accessible_resources.append(resource)
        
        resources = accessible_resources
    
    # Sérialiser et retourner les ressources
    serializer = DataLakeResourceSerializer(resources, many=True)
    return Response(serializer.data)

# Vues pour la partie V: Fonctionnalités avancées

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def full_text_search(request):
    """
    Recherche en texte intégral à travers toutes les données
    """
    try:
        # Récupérer les paramètres de recherche
        search_text = request.query_params.get('q')
        start_date = request.query_params.get('start_date')
        
        if not search_text:
            return Response(
                {"error": "Search query parameter 'q' is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            start_datetime = None
        
        # Initialiser les résultats
        search_results = {
            'query': search_text,
            'start_date': start_date,
            'timestamp': datetime.now(),
            'results': [],
            'alternative_technology': {
                'recommendation': 'Elasticsearch',
                'reason': 'For full-text search capabilities across a data lake, Elasticsearch provides better performance, scalability, and search features than a traditional database.'
            }
        }
        
        # Rechercher dans les transactions
        transaction_query = Q(transaction_id__icontains=search_text)
        transaction_query |= Q(payment_method__icontains=search_text)
        transaction_query |= Q(status__icontains=search_text)
        transaction_query |= Q(country__icontains=search_text)
        
        if start_datetime:
            transaction_query &= Q(timestamp__gte=start_datetime)
        
        transactions = Transaction.objects.filter(transaction_query)
        
        if transactions.exists():
            for transaction in transactions:
                search_results['results'].append({
                    'type': 'transaction',
                    'id': transaction.transaction_id,
                    'data': TransactionSerializer(transaction).data,
                    'resource': 'transactions_table'
                })
        
        # Rechercher dans les produits
        product_query = Q(product_id__icontains=search_text)
        product_query |= Q(product_name__icontains=search_text)
        product_query |= Q(category__icontains=search_text)
        
        products = ProductPurchase.objects.filter(product_query)
        
        # Appliquer le filtre de date indirectement via les transactions associées
        if start_datetime and products.exists():
            products = products.filter(transaction__timestamp__gte=start_datetime)
        
        # Ajouter les produits aux résultats
        if products.exists():
            for product in products:
                search_results['results'].append({
                    'type': 'product',
                    'id': product.product_id,
                    'data': ProductPurchaseSerializer(product).data,
                    'resource': 'product_purchases_table'
                })
        
        
        return Response(search_results)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def train_ml_model(request):
    """
    Endpoint RPC pour déclencher l'entraînement d'un modèle de ML
    """
    try:
        # Récupérer les paramètres pour l'entraînement
        model_type = request.data.get('model_type', 'recommendation')
        dataset = request.data.get('dataset', 'transactions')
        parameters = request.data.get('parameters', {})
        
        
        response = {
            'job_id': 'ml_training_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'status': 'started',
            'model_type': model_type,
            'dataset': dataset,
            'parameters': parameters,
            'estimated_completion_time': (datetime.now() + timedelta(minutes=30)).isoformat(),
            'message': 'Model training job has been submitted and is now processing'
        }
        
        return Response(response)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def repush_transaction(request, transaction_id):
    """
    Repousse une transaction spécifique au début du pipeline
    """
    try:
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
        
        transaction.processed = False
        
        transaction.timestamp = datetime.now()
        
        transaction.version += 1
        
        transaction.save()
        
        response = {
            'message': f'Transaction {transaction_id} has been repushed to the pipeline',
            'new_timestamp': transaction.timestamp.isoformat(),
            'new_version': transaction.version,
            'status': 'pending_processing'
        }
        
        return Response(response)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def repush_all_transactions(request):
    """
    Repousse toutes les transactions au début du pipeline
    """
    try:
        transactions = Transaction.objects.all()
        count = transactions.count()
        
        current_time = datetime.now()
        
        for transaction in transactions:
            transaction.processed = False
            
            transaction.timestamp = current_time
            
            transaction.version += 1
            
            transaction.save()
        
        response = {
            'message': f'{count} transactions have been repushed to the pipeline',
            'timestamp': current_time.isoformat(),
            'status': 'pending_processing'
        }
        
        return Response(response)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
