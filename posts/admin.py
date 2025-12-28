from django.contrib import admin
from .models import Cliente, Post

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'instagram_user')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'cliente', 'data_postagem', 'status', 'rede_social')
    list_filter = ('status', 'cliente', 'rede_social')
    search_fields = ('titulo', 'descricao_legenda')