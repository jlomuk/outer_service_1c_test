from django.urls import path

from . import views

urlpatterns = [
    path('get_employees/', views.get_employees),
]
