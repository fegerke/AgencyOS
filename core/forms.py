from django import forms
from .models import Agencia, Cliente, Post

# Opções para as redes sociais
REDES_OPCOES = [
    ('instagram', 'Instagram'),
    ('facebook', 'Facebook'),
    ('linkedin', 'LinkedIn'),
    ('tiktok', 'TikTok'),
    ('youtube', 'YouTube'),
    ('linktree', 'Linktree'),
]

class AgenciaForm(forms.ModelForm):
    class Meta:
        model = Agencia
        fields = [
            'nome_fantasia', 'razao_social', 'cnpj', 'email', 'telefone', 
            'logo', 'cep', 'logradouro', 'numero', 'complemento', 
            'bairro', 'cidade', 'estado'
        ]
        widgets = {
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cnpj', 'autocomplete': 'off'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_telefone'}), # Adicionado ID aqui
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cep', 'autocomplete': 'off'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cidade', 'autocomplete': 'off'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ClienteForm(forms.ModelForm):
    documento = forms.CharField(
        label="CPF ou CNPJ", 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'doc_field', 'autocomplete': 'off'})
    )

    class Meta:
        model = Cliente
        fields = [
            'tipo_pessoa', 'nome_fantasia', 'razao_social', 'email', 'telefone', 
            'nome_contato', 'whatsapp_contato', 'cep', 'logradouro', 
            'numero', 'complemento', 'bairro', 'cidade', 'estado'
        ]
        labels = {
            'whatsapp_contato': 'Telefone Contato', # Renomeado aqui
        }
        widgets = {
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_telefone'}),
            'whatsapp_contato': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_whatsapp_contato', 'autocomplete': 'off'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_cidade', 'autocomplete': 'off'}),
            # ... demais campos permanecem iguais
        }

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['cliente', 'titulo', 'data_publicacao', 'rede_social', 'status', 'legenda', 'briefing_arte', 'imagem_preview']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'data_publicacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rede_social': forms.Select(attrs={'class': 'form-control'}, choices=REDES_OPCOES),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'legenda': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'briefing_arte': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagem_preview': forms.FileInput(attrs={'class': 'form-control'}),
        }