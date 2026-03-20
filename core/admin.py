from django.contrib import admin
from .models import Agencia, Cliente, Cronograma, Post, DropboxConfig

@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    def get_socios(self, obj):
        return ", ".join([u.username for u in obj.socios.all()])
    get_socios.short_description = 'Sócios'

    list_display = ('nome_fantasia', 'email', 'get_socios', 'data_cadastro')
    search_fields = ('nome_fantasia', 'email')
    # ISSO AQUI CRIA A CAIXINHA DUPLA (MUITO MELHOR):
    filter_horizontal = ('socios',) 

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    def get_usuarios(self, obj):
        return ", ".join([u.username for u in obj.usuarios.all()])
    get_usuarios.short_description = 'Usuários com Acesso'

    list_display = ('nome_fantasia', 'agencia', 'email', 'get_usuarios')
    list_filter = ('agencia',)
    search_fields = ('nome_fantasia', 'email')
    # ISSO AQUI CRIA A CAIXINHA DUPLA NO CLIENTE TAMBÉM:
    filter_horizontal = ('usuarios',)

@admin.register(Cronograma)
class CronogramaAdmin(admin.ModelAdmin):
    # Adicionamos a rede_social na listagem e nos filtros do Cronograma
    list_display = ('titulo', 'cliente', 'rede_social', 'mes', 'ano', 'excluido')
    list_filter = ('rede_social', 'mes', 'ano', 'excluido', 'cliente')
    search_fields = ('titulo', 'cliente__nome_fantasia')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # Removemos a rede_social daqui e adicionamos o formato
    list_display = ('titulo', 'cronograma', 'feed', 'formato', 'status', 'data_publicacao', 'excluido')
    # Trocamos o filtro de rede_social para filtrar pelo formato e status
    list_filter = ('status', 'formato', 'excluido', 'data_publicacao')
    search_fields = ('titulo', 'legenda', 'cronograma__titulo')

@admin.register(DropboxConfig)
class DropboxConfigAdmin(admin.ModelAdmin):
    list_display = ('agencia', 'expires_at')