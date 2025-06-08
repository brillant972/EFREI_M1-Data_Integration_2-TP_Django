from django.contrib import admin
from .models import (
    ResourceAccess, APIRequestLog, Transaction, 
    ProductPurchase, DataLakeResource
)

# Personnalisation de l'affichage des modèles dans l'admin

@admin.register(ResourceAccess)
class ResourceAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource_type', 'resource_path', 'can_read', 'can_write', 'granted_by', 'created_at')
    list_filter = ('resource_type', 'can_read', 'can_write')
    search_fields = ('user__username', 'resource_path')
    date_hierarchy = 'created_at'

@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'endpoint', 'method', 'response_code', 'ip_address')
    list_filter = ('method', 'response_code')
    search_fields = ('user__username', 'endpoint', 'request_path')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'endpoint', 'method', 'request_path', 'request_body', 'response_code', 'ip_address', 'timestamp')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'amount', 'payment_method', 'status', 'country', 'timestamp')
    list_filter = ('payment_method', 'status', 'country')
    search_fields = ('transaction_id', 'user__username', 'country')
    date_hierarchy = 'timestamp'

@admin.register(ProductPurchase)
class ProductPurchaseAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'category', 'price', 'quantity', 'transaction')
    list_filter = ('category',)
    search_fields = ('product_id', 'product_name', 'category')

@admin.register(DataLakeResource)
class DataLakeResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource_type', 'path', 'version_control', 'created_at')
    list_filter = ('resource_type', 'version_control')
    search_fields = ('name', 'path', 'description')
    date_hierarchy = 'created_at'
