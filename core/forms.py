from django import forms
from .models import Agencia, Cliente, Post, Cronograma, PostArquivo, REDES_OPCOES, FORMATO_CHOICES, Feed
from django.contrib.auth.models import User
from datetime import datetime

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class AgenciaForm(forms.ModelForm):
    class Meta:
        model = Agencia
        fields = ['nome_fantasia', 'razao_social', 'cnpj', 'email', 'telefone', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep', 'logo', 'cor_personalizada']
        widgets = {
            'cnpj': forms.TextInput(attrs={'class': 'form-control mask-cnpj', 'id': 'id_cnpj', 'autocomplete': 'off'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-tel', 'id': 'id_telefone', 'autocomplete': 'off'}),
            'cep': forms.TextInput(attrs={'class': 'form-control mask-cep', 'id': 'id_cep', 'autocomplete': 'off'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'cor_personalizada': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }

class ClienteForm(forms.ModelForm):
    tipo_pessoa = forms.ChoiceField(
        choices=[('PF', 'PESSOA FÍSICA'), ('PJ', 'PESSOA JURÍDICA')],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_pessoa'})
    )
    class Meta:
        model = Cliente
        fields = ['tipo_pessoa', 'nome_fantasia', 'razao_social', 'cnpj', 'cpf', 'email', 'telefone', 'nome_contato', 'whatsapp_contato', 'logo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cor_personalizada']
        widgets = {
            'cnpj': forms.TextInput(attrs={'class': 'form-control mask-cnpj', 'id': 'id_cnpj', 'autocomplete': 'off'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control mask-cpf', 'id': 'id_cpf', 'autocomplete': 'off'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-tel', 'id': 'id_telefone', 'autocomplete': 'off'}),
            'whatsapp_contato': forms.TextInput(attrs={'class': 'form-control mask-tel', 'id': 'id_whatsapp_contato', 'autocomplete': 'off'}),
            'cep': forms.TextInput(attrs={'class': 'form-control mask-cep', 'id': 'id_cep', 'autocomplete': 'off'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cor_personalizada': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }

class CronogramaForm(forms.ModelForm):
    class Meta:
        model = Cronograma
        fields = ['cliente', 'titulo', 'rede_social', 'mes', 'ano', 'data_inicio', 'data_fim']
        
        # 1. Ajusta os textos que aparecem na tela para não parecer redundante
        labels = {
            'mes': 'Mês de Referência',
            'ano': 'Ano',
            'data_inicio': 'Primeiro Post',
            'data_fim': 'Último Post',
        }
        
        # 2. Adiciona o hover (tooltip) para explicar a integração com a nuvem
        widgets = {
            'mes': forms.NumberInput(attrs={
                'class': 'form-control', 
                'title': 'Usado para organizar a estrutura de pastas no Dropbox/Drive (Ex: 02 - FEVEREIRO).',
                'data-bs-toggle': 'tooltip',
                'data-bs-placement': 'top'
            }),
            'ano': forms.NumberInput(attrs={
                'class': 'form-control', 
                'title': 'Usado para organizar a estrutura de pastas no Dropbox/Drive.',
                'data-bs-toggle': 'tooltip',
                'data-bs-placement': 'top'
            }),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'rede_social': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CronogramaForm, self).__init__(*args, **kwargs)
        
        hoje = datetime.now()
        if not self.instance.pk:
            self.fields['mes'].initial = hoje.month
            self.fields['ano'].initial = hoje.year

        if user and hasattr(user, 'minha_agencia'):
            self.fields['cliente'].queryset = Cliente.objects.filter(agencia=user.minha_agencia)

class FeedForm(forms.ModelForm):
    class Meta:
        model = Feed
        fields = ['numero', 'titulo']
        labels = {
            'numero': 'Número do Feed',
            'titulo': 'Título (Ex: Feed 01)'
        }
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PostForm(forms.ModelForm):
    arquivos_multiplos = MultipleFileField(label="Arquivos do Post", required=False)

    class Meta:
        model = Post
        # REMOVIDO 'rede_social' DAQUI
        fields = ['cronograma', 'formato', 'titulo', 'data_publicacao', 'legenda', 'briefing_arte', 'status']
        labels = {
            'legenda': 'Legenda (Texto da publicação)',
            'briefing_arte': 'Instruções / Observações (Briefing para arte)',
        }
        widgets = {
            'data_publicacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'legenda': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Digite aqui o texto que será postado...'}),
            'briefing_arte': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Instruções para o designer ou editor...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # A lógica de filtrar as redes_sociais foi removida porque o post não escolhe mais a rede.
        # Apenas mantivemos a inicialização da data_publicacao
        if self.instance and self.instance.data_publicacao:
            self.fields['data_publicacao'].initial = self.instance.data_publicacao

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(label="Confirmar Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("As senhas não conferem.")
        return cleaned_data