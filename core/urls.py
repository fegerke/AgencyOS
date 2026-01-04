from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'), 
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('cliente/novo/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('agencia/configurar/', views.configurar_agencia, name='configurar_agencia'),
    path('post/novo/', views.cadastrar_post, name='cadastrar_post'),
]