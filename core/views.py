from django.shortcuts import render, redirect
from .forms import AgenciaForm, ClienteForm
from .models import Agencia, Cliente
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def home(request):
    # Pega a agência do usuário logado
    try:
        agencia = request.user.minha_agencia
        total_clientes = agencia.clientes.count()
    except Agencia.DoesNotExist:
        agencia = None
        total_clientes = 0
        
    return render(request, 'core/index.html', {
        'agencia': agencia,
        'total_clientes': total_clientes
    })

@login_required
def cadastrar_agencia(request):
    try:
        agencia_instancia = request.user.minha_agencia
    except Agencia.DoesNotExist:
        agencia_instancia = None

    if request.method == 'POST':
        form = AgenciaForm(request.POST, request.FILES, instance=agencia_instancia)
        if form.is_valid():
            agencia = form.save(commit=False)
            agencia.dono = request.user
            agencia.save()
            messages.success(request, "Configurações da agência salvas!")
            return redirect('cadastrar_agencia')
    else:
        form = AgenciaForm(instance=agencia_instancia)
    return render(request, 'core/configurar_agencia.html', {'form': form})

@login_required
def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.agencia = request.user.minha_agencia
            cliente.save()
            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('cadastrar_cliente')
    else:
        form = ClienteForm()
    return render(request, 'core/cadastrar_cliente.html', {'form': form})