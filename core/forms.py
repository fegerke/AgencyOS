from django import forms
from .models import Agencia, Cliente

REDES_OPCOES = [
    ('instagram', 'Instagram'),
    ('facebook', 'Facebook'),
    ('tiktok', 'TikTok'),
    ('kwai', 'Kwai'),
    ('linkedin', 'LinkedIn'),
    ('youtube', 'YouTube'),
    ('linktree', 'Linktree'),
]

class AgenciaForm(forms.ModelForm):
    documento = forms.CharField(label="CPF ou CNPJ", widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'doc_field'}))
    class Meta:
        model = Agencia
        fields = ['nome_fantasia', 'razao_social', 'email', 'telefone', 'cep', 'endereco', 'bairro', 'cidade', 'estado', 'chave_pix', 'logo']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'id': 'phone_field'}), # Adicionado ID
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
            'chave_pix': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for codigo, nome in REDES_OPCOES:
            self.fields[f'rede_{codigo}'] = forms.CharField(label=f'@{nome}', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def save(self, commit=True):
        agencia = super().save(commit=False)
        doc = self.cleaned_data.get('documento', '').replace('.', '').replace('-', '').replace('/', '')
        if len(doc) <= 11: agencia.cpf, agencia.tipo_pessoa = doc, 'PF'
        else: agencia.cnpj, agencia.tipo_pessoa = doc, 'PJ'
        redes_final = {codigo: self.cleaned_data.get(f'rede_{codigo}') for codigo, nome in REDES_OPCOES if self.cleaned_data.get(f'rede_{codigo}')}
        agencia.redes_sociais = redes_final
        if commit: agencia.save()
        return agencia

class ClienteForm(forms.ModelForm):
    documento = forms.CharField(label="CPF ou CNPJ", widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'doc_field'}))
    class Meta:
        model = Cliente
        fields = ['nome_fantasia', 'razao_social', 'email', 'telefone', 'cep', 'endereco', 'bairro', 'cidade', 'estado', 'nome_contato', 'whatsapp_contato']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'id': 'phone_field'}), # ID para o telefone geral
            'whatsapp_contato': forms.TextInput(attrs={'class': 'form-control', 'id': 'whatsapp_field'}), # ID para o whatsapp do contato
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_contato': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for codigo, nome in REDES_OPCOES:
            self.fields[f'rede_{codigo}'] = forms.CharField(label=f'@{nome}', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def save(self, commit=True):
        cliente = super().save(commit=False)
        doc = self.cleaned_data.get('documento', '').replace('.', '').replace('-', '').replace('/', '')
        if len(doc) <= 11: cliente.cpf, cliente.tipo_pessoa = doc, 'PF'
        else: cliente.cnpj, cliente.tipo_pessoa = doc, 'PJ'
        redes_final = {codigo: self.cleaned_data.get(f'rede_{codigo}') for codigo, nome in REDES_OPCOES if self.cleaned_data.get(f'rede_{codigo}')}
        cliente.redes_sociais = redes_final
        if commit: cliente.save()
        return cliente