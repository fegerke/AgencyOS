import os
from django.db import models
from django.utils.text import slugify

# --- FUNÇÃO MÁGICA DE CAMINHOS ---
def caminho_arquivo_dropbox(instance, filename):
    # 0. NOME DA PASTA RAIZ (Aqui você define onde tudo fica guardado)
    PASTA_RAIZ = 'AgencyOS_Uploads' 
    
    # 1. Pega o nome do cliente e remove acentos/espaços
    cliente_clean = slugify(instance.cliente.nome) 
    
    # 2. Pega as datas do post
    ano = instance.data_postagem.strftime('%Y')
    mes = instance.data_postagem.strftime('%m')
    dia = instance.data_postagem.strftime('%d')
    
    # 3. Cria o nome do evento (Dia + primeiros 30 caracteres do título)
    titulo_limpo = slugify(instance.titulo[:30])
    evento_clean = f"{dia}-{titulo_limpo}"
    
    # 4. Pega o tipo de rede
    tipo_clean = slugify(instance.get_rede_social_display())

    # 5. Monta o caminho final com a PASTA RAIZ no começo:
    # Ex: AgencyOS_Uploads / pizzaria-do-ze / 2025 / 12 / 25-natal / instagram-reels / video.mp4
    return os.path.join(PASTA_RAIZ, cliente_clean, ano, mes, evento_clean, tipo_clean, filename)


# --- MODELOS (TABELAS) ---

class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    instagram_user = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

class Post(models.Model):
    STATUS_CHOICES = [
        ('ideia', '💡 Ideia/Pauta'),
        ('producao', '🎬 Em Produção'),
        ('revisao', '👀 Aguardando Revisão'),
        ('agendado', '🗓️ Agendado'),
        ('postado', '✅ Postado'),
    ]

    REDE_CHOICES = [
        ('reels', 'Instagram Reels'),
        ('feed', 'Instagram Feed'),
        ('stories', 'Instagram Stories'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube Shorts'),
    ]

    titulo = models.CharField("Título do Post", max_length=200)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Cliente")
    rede_social = models.CharField("Rede Social", max_length=20, choices=REDE_CHOICES, default='reels')
    descricao_legenda = models.TextField("Legenda/Descrição", help_text="Texto que será copiado para o post", blank=True)
    data_postagem = models.DateTimeField("Data/Hora da Postagem")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ideia')
    
    # NOVOS CAMPOS: Upload de Arquivo com caminho automático
    arquivo_video = models.FileField("Arquivo de Vídeo", upload_to=caminho_arquivo_dropbox, blank=True, null=True)
    arquivo_capa = models.ImageField("Capa do Vídeo", upload_to=caminho_arquivo_dropbox, blank=True, null=True)

    def __str__(self):
        return f"{self.cliente} - {self.titulo}"

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['data_postagem']