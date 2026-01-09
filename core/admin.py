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
    list_display = ('cliente', 'titulo', 'mes', 'ano', 'excluido')
    list_filter = ('mes', 'ano', 'excluido')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'cronograma', 'data_publicacao', 'status', 'rede_social')
    list_filter = ('status', 'rede_social', 'data_publicacao')
    search_fields = ('titulo',)

@admin.register(DropboxConfig)
class DropboxConfigAdmin(admin.ModelAdmin):
    list_display = ('agencia', 'expires_at')