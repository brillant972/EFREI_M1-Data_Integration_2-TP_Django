from django.urls import path
from . import views

urlpatterns = [
    path("test_json_view", views.test_json_view, name="test_json_view"),
    path("post_test_json_view", views.post_test_json_view, name="post_test_json_view"),
    path("products", views.products, name="products"),
    path("most_expensive_product", views.most_expensive_product, name="most_expensive_product"),
    path("add_product", views.add_product, name="add_product"),
    path("update_product/<int:product_id>", views.update_product, name="update_product"),
    ]