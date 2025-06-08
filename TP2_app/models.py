from django.db import models
from django.contrib.auth.models import User
import os
import json
from datetime import datetime

# Modèle pour gérer les droits d'accès aux ressources
class ResourceAccess(models.Model):
    # Types de ressources possibles
    RESOURCE_TYPES = (
        ('FILE', 'File System'),
        ('TABLE', 'Database Table'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_accesses')
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES)
    resource_path = models.CharField(max_length=255)  
    can_read = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_accesses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'resource_type', 'resource_path')
    
    def __str__(self):
        return f"{self.user.username} - {self.resource_path} - Read:{self.can_read} Write:{self.can_write}"

# Modèle pour enregistrer chaque requête API
class APIRequestLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    request_path = models.CharField(max_length=255)
    request_body = models.TextField(null=True, blank=True)
    response_code = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.endpoint} - {self.response_code}"

# Modèle pour les transactions
class Transaction(models.Model):
    PAYMENT_METHODS = (
        ('CREDIT_CARD', 'Credit Card'),
        ('PAYPAL', 'PayPal'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )
    
    transaction_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    country = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    customer_rating = models.IntegerField(null=True, blank=True)
    processed = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.transaction_id} - {self.amount} - {self.status}"

# Modèle pour les produits achetés
class ProductPurchase(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='product_purchases')
    product_id = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.product_name} ({self.quantity}) - {self.transaction.transaction_id}"

# Modèle pour les ressources du data lake
class DataLakeResource(models.Model):
    RESOURCE_TYPES = (
        ('FILE', 'File'),
        ('TABLE', 'Database Table'),
        ('API', 'External API'),
    )
    
    name = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES)
    path = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    version_control = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.resource_type})"
