from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ResourceAccess, APIRequestLog, Transaction, ProductPurchase, DataLakeResource

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ResourceAccessSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    granted_by_username = serializers.SerializerMethodField()
    
    class Meta:
        model = ResourceAccess
        fields = ['id', 'username', 'resource_type', 'resource_path', 
                  'can_read', 'can_write', 'granted_by_username', 
                  'created_at', 'updated_at']
    
    def get_username(self, obj):
        return obj.user.username
    
    def get_granted_by_username(self, obj):
        if obj.granted_by:
            return obj.granted_by.username
        return None

class APIRequestLogSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = APIRequestLog
        fields = ['id', 'username', 'endpoint', 'method', 'request_path', 
                  'request_body', 'response_code', 'ip_address', 'timestamp']
    
    def get_username(self, obj):
        if obj.user:
            return obj.user.username
        return None

class ProductPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPurchase
        fields = ['id', 'product_id', 'product_name', 'category', 
                  'price', 'quantity']

class TransactionSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    product_purchases = ProductPurchaseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_id', 'username', 'amount', 
                  'payment_method', 'status', 'country', 'timestamp', 
                  'customer_rating', 'processed', 'version', 
                  'product_purchases']
    
    def get_username(self, obj):
        return obj.user.username

class DataLakeResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataLakeResource
        fields = ['id', 'name', 'resource_type', 'path', 'description', 
                  'version_control', 'created_at', 'updated_at']
