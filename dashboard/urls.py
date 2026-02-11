from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard URLs will be added here
    path('', views.index, name='index'),
]