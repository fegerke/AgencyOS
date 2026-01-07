from django import forms
from .models import Agencia, Cliente, Post, Cronograma, REDES_OPCOES, FORMATO_CHOICES
from django.contrib.auth.models import User
from datetime import datetime

class AgenciaForm(forms.ModelForm):
    class Meta:
        model = Agencia
        fields = ['nome_fantasia', 'razao_social', 'cnpj', 'email', 'telefone', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep', 'logo']
        widgets = {
            'cnpj': forms.TextInput(attrs={'class': 'form-control mask-cnpj', 'id': 'id_cnpj', 'autocomplete': 'off'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-tel', 'id': 'id_telefone', 'autocomplete': 'off'}),
            'cep': forms.TextInput(attrs={'class': 'form-control mask-cep', 'id': 'id_cep', 'autocomplete': 'off'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class ClienteForm(forms.ModelForm):
    tipo_pessoa = forms.ChoiceField(
        choices=[('PF', 'PESSOA FÍSICA'), ('PJ', 'PESSOA JURÍDICA')],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_pessoa'})
    )
    class Meta:
        model = Cliente
        fields = ['tipo_pessoa', 'nome_fantasia', 'razao_social', 'cnpj', 'cpf', 'email', 'telefone', 'nome_contato', 'whatsapp_contato', 'logo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado']
        widgets = {
            'cnpj': forms.TextInput(attrs={'class': 'form-control mask-cnpj', 'id': 'id_cnpj', 'autocomplete': 'off'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control mask-cpf', 'id': 'id_cpf', 'autocomplete': 'off'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control mask-tel', 'id': 'id_telefone', 'autocomplete': 'off'}),
            'whatsapp_contato': forms.TextInput(attrs={'class': 'form-control mask-tel', 'id': 'id_whatsapp_contato', 'autocomplete': 'off'}),
            'cep': forms.TextInput(attrs={'class': 'form-control mask-cep', 'id': 'id_cep', 'autocomplete': 'off'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class CronogramaForm(forms.ModelForm): # CORRIGIDO AQUI
    MESES_CHOICES = [(i, name) for i, name in enumerate(['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], 1)]
    current_year = datetime.now().year
    ANOS_CHOICES = [(y, y) for y in range(current_year - 1, current_year + 5)]

    mes = forms.ChoiceField(choices=MESES_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    ano = forms.ChoiceField(choices=ANOS_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Cronograma
        fields = ['cliente', 'titulo', 'mes', 'ano']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ano'].initial = datetime.now().year

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['cronograma', 'titulo', 'data_publicacao', 'rede_social', 'formato', 'legenda', 'briefing_arte', 'status', 'imagem_preview']
        widgets = {
            'data_publicacao': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'imagem_preview': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get('cronograma') or self.instance.pk:
            crono = self.initial.get('cronograma') or self.instance.cronograma
            # Filtro de redes sociais ativas do cliente
            redes_ativas = crono.cliente.redes_sociais.keys()
            self.fields['rede_social'].choices = [(id, nome) for id, nome in REDES_OPCOES if id in redes_ativas]
            if 'instagram' in redes_ativas:
                self.fields['rede_social'].initial = 'instagram'
        
        if self.instance and self.instance.data_publicacao:
            self.fields['data_publicacao'].initial = self.instance.data_publicacao.strftime('%Y-%m-%d')

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(label="Confirmar Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("As senhas não conferem!")