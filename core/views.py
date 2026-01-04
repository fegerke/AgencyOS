from django.shortcuts import render, redirect, get_object_or_404
from .forms import AgenciaForm, ClienteForm, REDES_OPCOES
from .models import Agencia, Cliente
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def home(request):
    # Busca a agência do usuário logado usando a relação OneToOne
    agencia = getattr(request.user, 'minha_agencia', None)
    
    total_clientes = 0
    clientes_recentes = []
    
    if agencia:
        total_clientes = agencia.clientes.count()
        # Pega os últimos 5 clientes cadastrados
        clientes_recentes = agencia.clientes.all().order_by('-id')[:5]
        
    return render(request, 'core/index.html', {
        'agencia': agencia,
        'total_clientes': total_clientes,
        'clientes_recentes': clientes_recentes,
        'total_redes': 0 # Futuramente podemos somar as redes ativas aqui
    })

@login_required
def listar_clientes(request):
    agencia = getattr(request.user, 'minha_agencia', None)
    clientes = []
    if agencia:
        clientes = agencia.clientes.all().order_by('nome_fantasia')
    
    return render(request, 'core/listar_clientes.html', {'clientes': clientes})

@login_required
def cadastrar_cliente(request):
    agencia_logada = getattr(request.user, 'minha_agencia', None)
    
    if not agencia_logada:
        messages.error(request, "Você precisa configurar sua agência antes de cadastrar clientes.")
        return redirect('configurar_agencia')

    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.agencia = agencia_logada
            
            # Lógica para processar as redes sociais vindas do formulário manual
            dados_redes = {}
            for codigo, nome in REDES_OPCOES:
                perfil = request.POST.get(f'perfil_{codigo}')
                login = request.POST.get(f'login_{codigo}')
                senha = request.POST.get(f'senha_{codigo}')
                
                if perfil or login: # Só salva se houver algum dado
                    dados_redes[codigo] = {
                        'perfil': perfil,
                        'login': login,
                        'senha': senha
                    }
            
            cliente.redes_sociais = dados_redes
            cliente.save()
            
            messages.success(request, f"Cliente {cliente.nome_fantasia} cadastrado com sucesso!")
            return redirect('index') # Redireciona para o dashboard
    else:
        form = ClienteForm()

    return render(request, 'core/cadastrar_cliente.html', {
        'form': form,
        'redes_opcoes': REDES_OPCOES
    })

@login_required
def configurar_agencia(request):
    # Busca a agência usando o getattr para evitar erros caso não exista
    agencia_instancia = getattr(request.user, 'minha_agencia', None)

    if request.method == 'POST':
        form = AgenciaForm(request.POST, request.FILES, instance=agencia_instancia)
        if form.is_valid():
            agencia = form.save(commit=False)
            agencia.dono = request.user
            agencia.save()
            messages.success(request, "Dados da agência atualizados com sucesso!")
            return redirect('index')
    else:
        form = AgenciaForm(instance=agencia_instancia)

    return render(request, 'core/configurar_agencia.html', {
        'form': form,
        'redes_opcoes': REDES_OPCOES
    })