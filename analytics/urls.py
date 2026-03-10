from django.urls import path
from . import views

urlpatterns = [
    path('beacon/', views.beacon_receiver, name='beacon_receiver'),
]
