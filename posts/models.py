from django.db import models

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
    descricao_legenda = models.TextField("Legenda/Descrição", help_text="Texto que será copiado para o post")
    data_postagem = models.DateTimeField("Data/Hora da Postagem")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ideia')
    
    # Links para o Dropbox
    link_video_dropbox = models.URLField("Link do Vídeo (Dropbox)", max_length=500, blank=True, null=True)
    link_capa_dropbox = models.URLField("Link da Capa (Dropbox)", max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.cliente} - {self.titulo}"

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['data_postagem']