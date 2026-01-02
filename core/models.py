from django.db import models
from django.contrib.auth.models import User

class BaseEmpresa(models.Model):
    TIPO_PESSOA_CHOICES = [('PF', 'Pessoa Física'),('PJ', 'Pessoa Jurídica')]
    tipo_pessoa = models.CharField(max_length=2, choices=TIPO_PESSOA_CHOICES, default='PJ')
    nome_fantasia = models.CharField(max_length=200, verbose_name="Nome Fantasia")
    razao_social = models.CharField(max_length=200, blank=True, null=True)
    cnpj = models.CharField(max_length=18, unique=True, blank=True, null=True)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        abstract = True

class Agencia(BaseEmpresa):
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='minha_agencia')
    logo = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    chave_pix = models.CharField(max_length=100, blank=True, null=True)
    cep = models.CharField(max_length=9, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    redes_sociais = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.nome_fantasia

class Cliente(BaseEmpresa):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='clientes')
    cep = models.CharField(max_length=9, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    
    # Campos de Contato Direto
    nome_contato = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pessoa de Contato")
    whatsapp_contato = models.CharField(max_length=20, blank=True, null=True, verbose_name="WhatsApp do Contato")
    
    redes_sociais = models.JSONField(default=dict, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_fantasia