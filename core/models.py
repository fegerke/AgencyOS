from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone

REDES_OPCOES = [
    ('linktree', 'Linktree'),
    ('instagram', 'Instagram'),
    ('facebook', 'Facebook'),
    ('linkedin', 'LinkedIn'),
    ('tiktok', 'TikTok'),
    ('youtube', 'YouTube'),
]

FORMATO_CHOICES = [
    ('feed_estatico', 'Feed - Foto Única'),
    ('feed_carrossel', 'Feed - Carrossel'),
    ('reels', 'Reels (Vídeo Vertical)'),
    ('stories', 'Stories (Foto/Vídeo)'),
    ('video_longo', 'Vídeo Longo (YouTube)'),
]

STATUS_CHOICES = [
    ('planejamento', 'Planejamento'),
    ('redacao', 'Em Redação'),
    ('design', 'Em Design'),
    ('aprovacao', 'Aguardando Aprovação'),
    ('ajuste', 'Ajuste Solicitado'),
    ('agendado', 'Agendado'),
    ('postado', 'Postado'),
]

class BaseEndereco(models.Model):
    cep = models.CharField(max_length=9, blank=True, null=True)
    logradouro = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    complemento = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    class Meta: abstract = True

class BaseEmpresa(models.Model):
    nome_fantasia = models.CharField(max_length=255)
    razao_social = models.CharField(max_length=255, blank=True, null=True)
    cnpj = models.CharField(max_length=18, blank=True, null=True)
    cpf = models.CharField(max_length=14, blank=True, null=True)
    tipo_pessoa = models.CharField(max_length=2, choices=[('PF', 'PESSOA FISICA'), ('PJ', 'PESSOA JURÍDICA')], default='PJ')
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    redes_sociais = models.JSONField(default=dict, blank=True)
    data_cadastro = models.DateTimeField(default=timezone.now)
    class Meta: abstract = True

class Agencia(BaseEmpresa, BaseEndereco):
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='minha_agencia')
    def __str__(self): return self.nome_fantasia

class Cliente(BaseEmpresa, BaseEndereco):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='clientes')
    usuario_acesso = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cliente_vinculado')
    nome_contato = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_contato = models.CharField(max_length=20, blank=True, null=True)
    def __str__(self): return self.nome_fantasia

class Cronograma(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='cronogramas')
    titulo = models.CharField(max_length=100, default="Geral")
    mes = models.IntegerField()
    ano = models.IntegerField()
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    excluido = models.BooleanField(default=False)
    data_exclusao = models.DateTimeField(null=True, blank=True)
    
    def __str__(self): 
        return f"{self.cliente.nome_fantasia} - {self.titulo} ({self.mes}/{self.ano})"

class Post(models.Model):
    cronograma = models.ForeignKey(Cronograma, on_delete=models.CASCADE, related_name='posts')
    titulo = models.CharField(max_length=200)
    data_publicacao = models.DateField()
    rede_social = models.CharField(max_length=20, choices=REDES_OPCOES)
    formato = models.CharField(max_length=50, choices=FORMATO_CHOICES)
    legenda = models.TextField(blank=True, null=True)
    briefing_arte = models.TextField(blank=True, null=True)
    imagem_preview = models.FileField(upload_to='posts/previews/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planejamento')
    dropbox_path = models.CharField(max_length=500, blank=True, null=True)
    excluido = models.BooleanField(default=False)
    data_exclusao = models.DateTimeField(null=True, blank=True)

    def gerar_caminho_dropbox(self):
        cli = slugify(self.cronograma.cliente.nome_fantasia)
        meses = {1:"01-JANEIRO", 2:"02-FEVEREIRO", 3:"03-MARCO", 4:"04-ABRIL", 5:"05-MAIO", 6:"06-JUNHO", 7:"07-JULHO", 8:"08-AGOSTO", 9:"09-SETEMBRO", 10:"10-OUTUBRO", 11:"11-NOVEMBRO", 12:"12-DEZEMBRO"}
        mes_nome = meses.get(self.cronograma.mes, str(self.cronograma.mes))
        crono_titulo = slugify(self.cronograma.titulo)
        
        if self.excluido:
            return f"AgencyOS/LIXEIRA/{cli}/{self.cronograma.ano}/{mes_nome}/{crono_titulo}/{slugify(self.titulo)}/"
        
        return f"AgencyOS/{cli}/{self.cronograma.ano}/{mes_nome}/{crono_titulo}/{slugify(self.titulo)}/"
    
    def gerar_caminho_base(self, lixeira=False):
        prefixo = "AgencyOS/LIXEIRA/CLIENTES" if lixeira else "AgencyOS/CLIENTES"
        cli = self.cronograma.cliente.nome_fantasia
        ano = str(self.cronograma.ano)
        meses = {1:"01 - JANEIRO", 2:"02 - FEVEREIRO", 3:"03 - MARCO", 4:"04 - ABRIL", 5:"05 - MAIO", 6:"06 - JUNHO", 7:"07 - JULHO", 8:"08 - AGOSTO", 9:"09 - SETEMBRO", 10:"10 - OUTUBRO", 11:"11 - NOVEMBRO", 12:"12 - DEZEMBRO"}
        mes_nome = meses.get(self.cronograma.mes)
        # Retorna o caminho da PASTA do post
        return f"/{prefixo}/{cli}/{ano}/{mes_nome}/{self.cronograma.titulo}/{self.titulo}/".replace("//", "/")

class PostArquivo(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='arquivos')
    arquivo = models.FileField(upload_to='posts/previews/')
    dropbox_path = models.CharField(max_length=500, blank=True, null=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordem']

    def __str__(self):
        return f"Arquivo {self.ordem} de {self.post.titulo}"

class DropboxConfig(models.Model):
    agencia = models.OneToOneField(Agencia, on_delete=models.CASCADE, related_name='dropbox_config')
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

# --- COLOCAR NO FINAL DO ARQUIVO core/models.py ---

from django.contrib.auth.models import User

@property
def minha_agencia_inteligente(self):
    # 1. Tenta ver se é Dono de Agência
    # (Supondo que no model Agencia o related_name seja 'agencia' ou padrão)
    if hasattr(self, 'agencia'):
        return self.agencia
    
    # 2. Tenta ver se é Sócia/Cliente
    # (O related_name que criamos no passo anterior foi 'cliente_vinculado')
    if hasattr(self, 'cliente_vinculado'):
        return self.cliente_vinculado.agencia
        
    return None

# Injeta essa propriedade dentro do User padrão do Django
User.add_to_class('minha_agencia', minha_agencia_inteligente)