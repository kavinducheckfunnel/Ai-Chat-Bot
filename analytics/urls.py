from django.urls import path
from . import views

urlpatterns = [
    path('beacon/', views.beacon_receiver, name='beacon_receiver'),
    path('client/<uuid:client_id>/', views.client_analytics, name='client_analytics'),
]
