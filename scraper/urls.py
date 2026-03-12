from django.urls import path
from . import views

urlpatterns = [
    path('webhooks/shopify/<uuid:client_id>/', views.shopify_webhook, name='shopify_webhook'),
    path('webhooks/woocommerce/<uuid:client_id>/', views.woocommerce_webhook, name='woocommerce_webhook'),
    path('webhooks/wordpress/<uuid:client_id>/', views.wordpress_webhook, name='wordpress_webhook'),
]
