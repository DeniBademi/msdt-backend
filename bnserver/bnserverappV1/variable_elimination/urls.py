from django.urls import path
from .views import predict

urlpatterns = [
    path('network/predict/', predict, name='predict'),
]

