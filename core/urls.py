from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('configurar-agencia/', views.configurar_agencia, name='configurar_agencia'),
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/novo/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('clientes/editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/excluir/<int:pk>/', views.excluir_cliente, name='excluir_cliente'),
    path('cronograma/novo/', views.cadastrar_cronograma, name='cadastrar_cronograma'),
    path('cronograma/<int:pk>/', views.detalhes_cronograma, name='detalhes_cronograma'),
    path('cronogramas/', views.listar_cronogramas, name='listar_cronogramas'),
    path('cronograma/excluir/<int:pk>/', views.excluir_cronograma, name='excluir_cronograma'),
    path('post/novo/', views.cadastrar_post, name='cadastrar_post'),
    path('post/editar/<int:pk>/', views.editar_post, name='editar_post'),
    path('post/excluir/<int:pk>/', views.excluir_post, name='excluir_post'),
    path('arquivo/excluir/<int:pk>/', views.excluir_arquivo_post, name='excluir_arquivo_post'),
    path('lixeira/', views.lixeira, name='lixeira'),
    path('lixeira/recuperar-post/<int:pk>/', views.recuperar_post, name='recuperar_post'),
    path('lixeira/recuperar-cronograma/<int:pk>/', views.recuperar_cronograma, name='recuperar_cronograma'),
    path('lixeira/limpar/', views.limpar_lixeira_total, name='limpar_lixeira_total'),
    path('convite-equipe-agency/', views.registro_equipe, name='registro_equipe'),
    path('conectar-dropbox/', views.conectar_dropbox, name='conectar_dropbox'),
    path('dropbox-callback/', views.dropbox_callback, name='dropbox_callback'),
    path('desconectar-dropbox/', views.desconectar_dropbox, name='desconectar_dropbox'),
    path('cronograma/<int:pk>/pdf/', views.gerar_pdf_cronograma, name='gerar_pdf_cronograma'),
]