from django.urls import path
from . import views

urlpatterns = [
    path('configuracoes/agencia/', views.cadastrar_agencia, name='cadastrar_agencia'),
    path('clientes/novo/', views.cadastrar_cliente, name='cadastrar_cliente'),
]