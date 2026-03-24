# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('configurar-agencia/', views.configurar_agencia, name='configurar_agencia'),
    
    # Clientes
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/novo/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('clientes/editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/excluir/<int:pk>/', views.excluir_cliente, name='excluir_cliente'),
    path('convites/novo/', views.gerar_convite, name='gerar_convite'),

    # Cargos e Funções
    path('funcoes/', views.gerenciar_funcoes, name='gerenciar_funcoes'),
    path('funcoes/editar/<int:funcao_id>/', views.gerenciar_funcoes, name='editar_funcao'),
    path('funcoes/excluir/<int:funcao_id>/', views.excluir_funcao, name='excluir_funcao'),

    # API Interna (Ajax)
    path('api/cliente/<int:cliente_id>/redes/', views.api_get_redes_cliente, name='api_get_redes_cliente'),
    
    # Cronogramas
    path('cronogramas/', views.listar_cronogramas, name='listar_cronogramas'),
    path('cronograma/novo/', views.cadastrar_cronograma, name='cadastrar_cronograma'),
    path('cronograma/<int:pk>/', views.detalhes_cronograma, name='detalhes_cronograma'),
    path('cronograma/excluir/<int:pk>/', views.excluir_cronograma, name='excluir_cronograma'),
    
    # Feeds - ROTA NOVA
    path('cronograma/<int:cronograma_id>/novo-feed/', views.cadastrar_feed, name='cadastrar_feed'),
    
    # PDF 
    path('cronograma/<int:cronograma_id>/gerar-pdf/', views.gerar_pdf_cronograma_view, name='gerar_pdf_cronograma'),
    path('cronograma/<int:cronograma_id>/visualizar-pdf/', views.visualizar_pdf_cronograma_view, name='visualizar_pdf_cronograma'),
    path('cronograma/<int:cronograma_id>/testar-layout/', views.testar_layout_pdf, name='testar_layout_pdf'),
    path('cronograma/<int:cronograma_id>/check-pdf/', views.check_pdf_status, name='check_pdf_status'),

    # Posts - ROTA NOVA E ROTAS ANTIGAS
    path('feed/<int:feed_id>/novo-post/', views.cadastrar_post, name='cadastrar_post'), # <-- ROTA ATUALIZADA
    path('post/editar/<int:pk>/', views.editar_post, name='editar_post'),
    path('post/excluir/<int:pk>/', views.excluir_post, name='excluir_post'),
    path('arquivo/excluir/<int:pk>/', views.excluir_arquivo_post, name='excluir_arquivo_post'),
    
    # Lixeira
    path('lixeira/', views.lixeira, name='lixeira'),
    path('lixeira/recuperar-post/<int:pk>/', views.recuperar_post, name='recuperar_post'),
    path('lixeira/recuperar-cronograma/<int:pk>/', views.recuperar_cronograma, name='recuperar_cronograma'),
    path('lixeira/limpar/', views.limpar_lixeira_total, name='limpar_lixeira_total'),
    
    # Auth & Dropbox
    path('convite-equipe-agency/', views.registro_equipe, name='registro_equipe'),
    path('conectar-dropbox/', views.conectar_dropbox, name='conectar_dropbox'),
    path('dropbox-callback/', views.dropbox_callback, name='dropbox_callback'),
    path('desconectar-dropbox/', views.desconectar_dropbox, name='desconectar_dropbox'),
]