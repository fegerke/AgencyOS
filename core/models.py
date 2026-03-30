from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    email = models.EmailField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    logo_dropbox_link = models.URLField(max_length=500, blank=True, null=True)
    redes_sociais = models.JSONField(default=dict, blank=True)
    data_cadastro = models.DateTimeField(default=timezone.now)
    class Meta: abstract = True

class Agencia(BaseEmpresa, BaseEndereco):
    socios = models.ManyToManyField(User, related_name='agencias_socio', blank=True)
    perfil_cliente = models.OneToOneField('Cliente', on_delete=models.SET_NULL, null=True, blank=True, related_name='agencia_vinculada')
    cor_personalizada = models.CharField(max_length=7, default="#6c5ce7", help_text="Cor Hex")
    def __str__(self): return self.nome_fantasia

class Cliente(BaseEmpresa, BaseEndereco):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='clientes')
    usuarios = models.ManyToManyField(User, related_name='clientes_acesso', blank=True)
    nome_contato = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_contato = models.CharField(max_length=20, blank=True, null=True)
    token_convite = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cor_personalizada = models.CharField(max_length=7, default="#6c5ce7", help_text="Cor em formato Hex (ex: #6c5ce7)")
    def __str__(self): return self.nome_fantasia

class Cronograma(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='cronogramas')
    titulo = models.CharField(max_length=100, default="Geral")
    rede_social = models.CharField(max_length=20, choices=REDES_OPCOES, default='instagram')
    mes = models.IntegerField()
    ano = models.IntegerField()
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    excluido = models.BooleanField(default=False)
    data_exclusao = models.DateTimeField(null=True, blank=True)
    pdf_dropbox_link = models.URLField(max_length=500, blank=True, null=True)
    pdf_dropbox_path = models.CharField(max_length=500, blank=True, null=True)
    
    def __str__(self): 
        return f"{self.cliente.nome_fantasia} - {self.titulo} ({self.get_rede_social_display()} - {self.mes}/{self.ano})"

class Feed(models.Model):
    cronograma = models.ForeignKey(Cronograma, on_delete=models.CASCADE, related_name='feeds')
    numero = models.IntegerField(default=1)
    titulo = models.CharField(max_length=100, default="Feed 01")

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f"{self.titulo} - {self.cronograma.titulo}"
    
class Post(models.Model):
    cronograma = models.ForeignKey(Cronograma, on_delete=models.CASCADE, related_name='posts')
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='posts', null=True, blank=True)
    titulo = models.CharField(max_length=200)
    data_publicacao = models.DateField()
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
        return f"/{prefixo}/{cli}/{ano}/{mes_nome}/{self.cronograma.titulo}/{self.titulo}/".replace("//", "/")

class PostArquivo(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='arquivos')
    arquivo = models.FileField(upload_to='posts/previews/')
    dropbox_path = models.CharField(max_length=500, blank=True, null=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta: ordering = ['ordem']
    def __str__(self): return f"Arquivo {self.ordem} de {self.post.titulo}"

class DropboxConfig(models.Model):
    agencia = models.OneToOneField(Agencia, on_delete=models.CASCADE, related_name='dropbox_config')
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

def get_agencia_inteligente(self):
    # 1. Se for Superusuário (Você)
    if self.is_superuser:
        from core.models import Agencia # Import local para não dar erro
        return Agencia.objects.first()
        
    # 2. Se for Sócio/Dono
    if self.agencias_socio.exists():
        return self.agencias_socio.first()
        
    # 3. Se for Colaborador (Usuário do convite)
    from core.models import Colaborador 
    colaborador = Colaborador.objects.filter(usuario=self).first()
    if colaborador:
        return colaborador.agencia
        
    return None

def check_is_equipe(self):
    if self.is_superuser: 
        return True
    if self.agencias_socio.exists(): 
        return True
    from core.models import Colaborador
    return Colaborador.objects.filter(usuario=self).exists()

# Gruda as funções no User como propriedades
User.add_to_class('minha_agencia', property(get_agencia_inteligente))
User.add_to_class('is_equipe', property(check_is_equipe))

class Funcao(models.Model):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='funcoes')
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True, help_text="Opcional. Ex: Responsável pelas artes.")

    class Meta:
        ordering = ['nome']
        unique_together = ('agencia', 'nome')

    def __str__(self):
        return self.nome

class Colaborador(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_colaborador')
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='colaboradores')
    funcoes = models.ManyToManyField(Funcao, blank=True, related_name='colaboradores')
    telefone = models.CharField(max_length=20, blank=True, null=True)
    foto = models.ImageField(upload_to='colaboradores/fotos/', blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username

class PerfilUsuarioCliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_cliente_user')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='perfis_usuarios')
    telefone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.cliente.nome_fantasia}"

class Convite(models.Model):
    TIPO_ESCOLHAS = (
        ('EQUIPE', 'Membro da Equipe'),
        ('CLIENTE', 'Cliente da Agência'),
    )
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='convites')
    nome = models.CharField(max_length=100, help_text="Nome de quem vai receber o convite")
    email = models.EmailField(help_text="E-mail principal para envio")
    tipo = models.CharField(max_length=10, choices=TIPO_ESCOLHAS, default='EQUIPE')
    cliente_vinculado = models.ForeignKey('Cliente', on_delete=models.CASCADE, null=True, blank=True, related_name='convites_enviados')
    funcoes = models.ManyToManyField(Funcao, blank=True, help_text="Quais funções essa pessoa terá na agência?")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    aceito = models.BooleanField(default=False)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"Convite para {self.nome} ({self.get_tipo_display()})"
    
    @property
    def link_whatsapp(self):
        return f"Olá {self.nome}! Aqui está o seu link de acesso ao AgencyOS: /convite/{self.token}"

@receiver(post_save, sender=Agencia)
def configurar_agencia_padrao(sender, instance, created, **kwargs):
    if not instance.perfil_cliente:
        novo_cliente = Cliente.objects.create(
            agencia=instance, nome_fantasia=instance.nome_fantasia, razao_social=instance.razao_social,
            cnpj=instance.cnpj, email=instance.email, cor_personalizada=instance.cor_personalizada,
            tipo_pessoa='PJ', logo=instance.logo
        )
        Agencia.objects.filter(pk=instance.pk).update(perfil_cliente=novo_cliente)
    else:
        cliente = instance.perfil_cliente
        cliente.nome_fantasia = instance.nome_fantasia; cliente.cor_personalizada = instance.cor_personalizada
        if instance.logo: cliente.logo = instance.logo
        cliente.save()

    if not Funcao.objects.filter(agencia=instance).exists():
        funcoes_padrao = ['Atendimento', 'Designer', 'Redator', 'Social Media', 'Gestor de Tráfego', 'Diretor de Arte', 'Desenvolvedor']
        for nome in funcoes_padrao:
            Funcao.objects.create(agencia=instance, nome=nome)