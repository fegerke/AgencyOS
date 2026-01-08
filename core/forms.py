from django import forms
from .models import Agencia, Cliente, Post, Cronograma, PostArquivo, REDES_OPCOES, FORMATO_CHOICES
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
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class CronogramaForm(forms.ModelForm):
    class Meta:
        model = Cronograma
        fields = ['cliente', 'titulo', 'mes', 'ano', 'data_inicio', 'data_fim']
        widgets = {
            # O format='%Y-%m-%d' é essencial para o <input type="date"> do navegador
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CronogramaForm, self).__init__(*args, **kwargs)
        
        # Preenchimento automático de Mês e Ano atuais
        hoje = datetime.now()
        if not self.instance.pk:  # Só preenche se for um novo registro
            self.fields['mes'].initial = hoje.month
            self.fields['ano'].initial = hoje.year

        if user and hasattr(user, 'minha_agencia'):
            self.fields['cliente'].queryset = Cliente.objects.filter(agencia=user.minha_agencia)

class PostForm(forms.ModelForm):
    arquivos_multiplos = MultipleFileField(label="Arquivos do Post", required=False)

    class Meta:
        model = Post
        fields = ['cronograma', 'rede_social', 'formato', 'titulo', 'data_publicacao', 'legenda', 'briefing_arte', 'status']
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
        crono = None
        if self.instance and hasattr(self.instance, 'cronograma') and self.instance.cronograma:
            crono = self.instance.cronograma
        elif 'initial' in kwargs and 'cronograma' in kwargs['initial']:
            crono = kwargs['initial']['cronograma']

        if self.instance and self.instance.data_publicacao:
            self.fields['data_publicacao'].initial = self.instance.data_publicacao

        if crono:
            redes_ativas = crono.cliente.redes_sociais.keys()
            self.fields['rede_social'].choices = [(id, nome) for id, nome in REDES_OPCOES if id in redes_ativas]

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