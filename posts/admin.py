from django.contrib import admin
from .models import Agencia, Cliente, Post, Tarefa, ArquivoTarefa

# Permite gerenciar arquivos dentro da tarefa
class ArquivoTarefaInline(admin.TabularInline):
    model = ArquivoTarefa
    extra = 1

# Permite gerenciar tarefas dentro do post (O pulo do gato!)
class TarefaInline(admin.TabularInline):
    model = Tarefa
    extra = 1 # Quantas linhas vazias aparecem por padrão
    show_change_link = True # Cria um link para editar a tarefa em tela cheia se precisar

@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug')
    prepopulated_fields = {'slug': ('nome',)}

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'agencia', 'instagram_user')
    list_filter = ('agencia',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # Removido 'status' daqui para corrigir o erro
    list_display = ('titulo', 'cliente', 'data_postagem', 'rede_social')
    list_filter = ('cliente__agencia', 'rede_social', 'cliente')
    search_fields = ('titulo',)
    inlines = [TarefaInline] # Adiciona as tarefas na mesma tela do post

@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'post', 'responsavel', 'prazo', 'status')
    list_filter = ('status', 'tipo', 'responsavel')
    inlines = [ArquivoTarefaInline]