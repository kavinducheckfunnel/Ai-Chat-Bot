"""Shopify OAuth + order-tracking routes, mounted at /api/shopify/."""
from django.urls import path
from . import shopify_oauth

urlpatterns = [
    path('authorize-url/', shopify_oauth.shopify_authorize_url, name='shopify_authorize_url'),
    path('oauth/callback', shopify_oauth.shopify_oauth_callback, name='shopify_oauth_callback'),
    path('disconnect/<uuid:client_id>/', shopify_oauth.shopify_disconnect, name='shopify_disconnect'),
    path('status/<uuid:client_id>/', shopify_oauth.shopify_status, name='shopify_status'),
    # GDPR mandatory webhooks (app review)
    path('gdpr/customers-data-request', shopify_oauth.shopify_gdpr_customers_data_request),
    path('gdpr/customers-redact', shopify_oauth.shopify_gdpr_customers_redact),
    path('gdpr/shop-redact', shopify_oauth.shopify_gdpr_shop_redact),
]
