from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Agencia, Cliente, Post
from .forms import AgenciaForm, ClienteForm, PostForm, REDES_OPCOES

@login_required
def home(request):
    agencia = getattr(request.user, 'minha_agencia', None)
    context = {
        'agencia': agencia,
        'total_clientes': Cliente.objects.filter(agencia=agencia).count() if agencia else 0,
        'posts_recentes': Post.objects.filter(cliente__agencia=agencia).order_by('-data_criacao')[:5] if agencia else []
    }
    return render(request, 'core/index.html', context)

@login_required
def configurar_agencia(request):
    agencia, created = Agencia.objects.get_or_create(dono=request.user)
    
    if request.method == 'POST':
        form = AgenciaForm(request.POST, request.FILES, instance=agencia)
        if form.is_valid():
            agencia = form.save(commit=False)
            
            novas_redes = {}
            for rede_id, rede_nome in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    novas_redes[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}', ''),
                        'usuario': request.POST.get(f'user_{rede_id}', ''),
                        'senha': request.POST.get(f'pass_{rede_id}', ''),
                    }
            
            agencia.redes_sociais = novas_redes 
            agencia.save()
            
            messages.success(request, "Configurações salvas!")
            return redirect('configurar_agencia')
    else:
        form = AgenciaForm(instance=agencia)

    return render(request, 'core/configurar_agencia.html', {
        'form': form,
        'agencia': agencia,
        'redes_disponiveis': REDES_OPCOES,
    })

@login_required
def listar_clientes(request):
    agencia = request.user.minha_agencia
    clientes = Cliente.objects.filter(agencia=agencia).exclude(eh_perfil_agencia=True)
    return render(request, 'core/listar_clientes.html', {'clientes': clientes})

@login_required
def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.agencia = request.user.minha_agencia
            
            # Lógica do documento unificado
            doc = request.POST.get('documento', '').replace('.', '').replace('/', '').replace('-', '')
            if len(doc) > 11:
                cliente.cnpj = doc
                cliente.cpf = None
            else:
                cliente.cpf = doc
                cliente.cnpj = None

            # Redes Sociais
            redes_cliente = {}
            for rede_id, rede_nome in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    redes_cliente[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}', ''),
                        'usuario': request.POST.get(f'user_{rede_id}', ''),
                        'senha': request.POST.get(f'pass_{rede_id}', ''),
                    }
            cliente.redes_sociais = redes_cliente
            cliente.save()
            
            messages.success(request, "Cliente cadastrado!")
            return redirect('listar_clientes')
    else:
        form = ClienteForm()
    return render(request, 'core/cadastrar_cliente.html', {'form': form, 'redes_disponiveis': REDES_OPCOES})

@login_required
def cadastrar_post(request):
    # Pega o cliente_id da URL se vier do botão "Novo Post" na lista de clientes
    cliente_id = request.GET.get('cliente')
    initial_data = {}
    if cliente_id:
        initial_data['cliente'] = get_object_or_404(Cliente, id=cliente_id, agencia=request.user.minha_agencia)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save()
            messages.success(request, "Post agendado com sucesso!")
            return redirect('home')
    else:
        form = PostForm(initial=initial_data)
        # Filtra para mostrar apenas clientes da agência do usuário no select
        form.fields['cliente'].queryset = Cliente.objects.filter(agencia=request.user.minha_agencia)
    
    return render(request, 'core/cadastrar_post.html', {'form': form})