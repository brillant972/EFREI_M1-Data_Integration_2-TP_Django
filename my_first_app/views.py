from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product
from .models import AccessRight
from django.core.paginator import Paginator


def check_access(endpoint_name):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                has_permission = AccessRight.objects.filter(user=request.user, endpoint=endpoint_name, can_access=True).exists()
                if has_permission:
                    return view_func(request, *args, **kwargs)
                return JsonResponse({"error": "Access denied"}, status=403)
            return JsonResponse({"error": "Authentication required"}, status=401)
        return wrapper
    return decorator

def test_json_view(request):
    data = {
    'name': 'John Doe',
    'age': 30,
    'location': 'New York',
    'is_active': True,
    }
    return JsonResponse(data)

@csrf_exempt
def post_test_json_view(request):
    if request.method == 'POST':
        try:
            request_data = json.loads(request.body)
            user_name = request_data.get('user', 'John Doe') 
            
            data = {
                'name': user_name,
                'age': 30,
                'location': 'New York',
                'is_active': True,
            }
            return JsonResponse(data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

   
def products(request):
    # GET: récupérer tous les produits avec pagination
    if request.method == 'GET':
        all_products = Product.objects.all()
        page_number = int(request.GET.get('page', 1))
        page_size = 3  # Lim à 3 produits par page
        
        paginator = Paginator(all_products, page_size)
        page_obj = paginator.get_page(page_number)
        
        response = {
            'products': list(page_obj.object_list.values()),
            'pagination': {
                'total_products': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        return JsonResponse(response)
    else:
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)
    

def most_expensive_product(request):
    # GET: récupérer le produit le plus cher
    if request.method == 'GET':
        product = Product.objects.order_by('-price').first()
        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'description': product.description,
        })
    else:
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)

@csrf_exempt
@check_access('add_product')    
def add_product(request):
    # POST: ajouter un nouveau produit
    if request.method == 'POST':
        request_data = json.loads(request.body)
        product = Product.objects.create(
                name=request_data['name'],
                price=request_data['price'],
                description=request_data.get('description', '')
            )
        return JsonResponse({
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'description': product.description,
            })
    else :
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

@csrf_exempt 
@check_access('update_product')   
def update_product(request, product_id):
    # PUT: mettre à jour un produit existant
    if request.method == 'PUT':
        try:
            request_data = json.loads(request.body)
            product = Product.objects.get(id=product_id)
            product.name = request_data.get('name', product.name)
            product.price = request_data.get('price', product.price)
            product.description = request_data.get('description', product.description)
            product.save()
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'description': product.description,
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        return JsonResponse({'error': 'Only PUT method is allowed'}, status=405)
    