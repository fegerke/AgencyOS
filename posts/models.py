import os
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User

# --- ORGANIZAÇÃO (O "Dono" do sistema - Para o modelo SaaS) ---
class Agencia(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.nome

# --- FUNÇÃO DE CAMINHOS (Organização automática de pastas) ---
def caminho_arquivo_dropbox(instance, filename):
    # instance pode ser um Post ou um ArquivoTarefa. Vamos tratar ambos:
    if hasattr(instance, 'post'):
        post_obj = instance.post
    elif hasattr(instance, 'tarefa'):
        post_obj = instance.tarefa.post
    else:
        post_obj = instance

    agencia_folder = slugify(post_obj.cliente.agencia.nome)
    cliente_folder = slugify(post_obj.cliente.nome)
    ano = post_obj.data_postagem.strftime('%Y')
    mes = post_obj.data_postagem.strftime('%m')
    
    return os.path.join(agencia_folder, cliente_folder, ano, mes, filename)

# --- MODELOS ---

class Cliente(models.Model):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='clientes')
    nome = models.CharField(max_length=100)
    instagram_user = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.agencia.nome})"

class Post(models.Model):
    REDE_CHOICES = [
        ('reels', 'Instagram Reels'),
        ('feed', 'Instagram Feed'),
        ('stories', 'Instagram Stories'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube Shorts'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    titulo = models.CharField("Título do Post", max_length=200)
    rede_social = models.CharField("Rede Social", max_length=20, choices=REDE_CHOICES, default='reels')
    data_postagem = models.DateTimeField("Data da Postagem")
    descricao_legenda = models.TextField("Legenda", blank=True)

    def __str__(self):
        return f"{self.cliente.nome} - {self.titulo}"

class Tarefa(models.Model):
    TIPO_CHOICES = [
        ('planejamento', '📝 Planejamento/Roteiro'),
        ('captacao', '🎥 Captação'),
        ('edicao', '🎬 Edição'),
        ('aprovacao', '✅ Aprovação'),
        ('postagem', '📱 Postagem'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('atrasado', 'Atrasado'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='tarefas')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prazo = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    local = models.CharField("Local (Se captação)", max_length=255, blank=True)
    observacoes = models.TextField("Instruções/Roteiro", blank=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.post.titulo}"

class ArquivoTarefa(models.Model):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name='arquivos')
    arquivo = models.FileField(upload_to=caminho_arquivo_dropbox)
    data_upload = models.DateTimeField(auto_now_add=True)
    descricao = models.CharField(max_length=100, blank=True)