from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Agencia, Cliente, Post, DropboxConfig, Cronograma, REDES_OPCOES
from .forms import AgenciaForm, ClienteForm, PostForm, CronogramaForm, UserRegistrationForm
import dropbox, requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

@login_required
def home(request):
    agencia = getattr(request.user, 'minha_agencia', None)
    context = {
        'agencia': agencia,
        'total_clientes': Cliente.objects.filter(agencia=agencia).count() if agencia else 0,
        'clientes_recentes': Cliente.objects.filter(agencia=agencia).order_by('-id')[:5] if agencia else [],
    }
    return render(request, 'core/index.html', context)

@login_required
def listar_cronogramas(request):
    agencia = getattr(request.user, 'minha_agencia', None)
    cronogramas = Cronograma.objects.filter(cliente__agencia=agencia).order_by('-ano', '-mes') if agencia else []
    return render(request, 'core/listar_cronogramas.html', {'cronogramas': cronogramas})

@login_required
def detalhes_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    
    if request.method == 'POST' and 'editar_cronograma' in request.POST:
        form_cronograma = CronogramaForm(request.POST, instance=cronograma)
        if form_cronograma.is_valid():
            form_cronograma.save()
            messages.success(request, "Dados do cronograma atualizados!")
            return redirect('detalhes_cronograma', pk=pk)
    else:
        form_cronograma = CronogramaForm(instance=cronograma)

    # Posts filtrados para não mostrar os excluídos
    posts = cronograma.posts.filter(excluido=False).order_by('data_publicacao')
    
    return render(request, 'core/detalhes_cronograma.html', {
        'cronograma': cronograma,
        'posts': posts,
        'form_cronograma': form_cronograma
    })

@login_required
def cadastrar_cronograma(request):
    if request.method == 'POST':
        form = CronogramaForm(request.POST)
        if form.is_valid():
            cronograma = form.save()
            messages.success(request, "Cronograma criado com sucesso!")
            return redirect('listar_cronogramas')
    else:
        form = CronogramaForm()
    return render(request, 'core/cadastrar_cronograma.html', {'form': form})

@login_required
def excluir_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    cronograma.excluido = True
    cronograma.data_exclusao = timezone.now()
    # Ao excluir cronograma, não movemos pastas do dropbox agora para não dar timeout, 
    # apenas marcamos no banco.
    cronograma.posts.all().update(excluido=True, data_exclusao=timezone.now())
    cronograma.save()
    messages.warning(request, "Cronograma enviado para a lixeira!")
    return redirect('listar_cronogramas')

@login_required
def cadastrar_post(request):
    cronograma_id = request.GET.get('cronograma')
    cronograma_obj = get_object_or_404(Cronograma, pk=cronograma_id, cliente__agencia=request.user.minha_agencia)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save()
            fazer_upload_dropbox(request, post)
            return JsonResponse({'status': 'success', 'url': f"/cronograma/{post.cronograma.id}/"})
    else:
        form = PostForm(initial={'cronograma': cronograma_obj})
    
    return render(request, 'core/cadastrar_post.html', {'form': form, 'cronograma_obj': cronograma_obj})

@login_required
def editar_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            if 'imagem_preview' in request.FILES:
                fazer_upload_dropbox(request, post)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'url': f"/cronograma/{post.cronograma.id}/"})
            return redirect('detalhes_cronograma', pk=post.cronograma.id)
    else:
        form = PostForm(instance=post)
    return render(request, 'core/cadastrar_post.html', {'form': form, 'editando': True})

@login_required
def excluir_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    caminho_antigo = post.dropbox_path
    
    post.excluido = True
    post.data_exclusao = timezone.now()
    
    if caminho_antigo:
        try:
            dbx_config = DropboxConfig.objects.get(agencia=request.user.minha_agencia)
            dbx = dropbox.Dropbox(oauth2_access_token=dbx_config.access_token, refresh_token=dbx_config.refresh_token,
                                  app_key=settings.DROPBOX_APP_KEY, app_secret=settings.DROPBOX_APP_SECRET)
            
            # Pega a pasta do post (um nível acima do arquivo)
            pasta_antiga = "/".join(caminho_antigo.split('/')[:-1])
            nova_pasta = "/" + post.gerar_caminho_dropbox()
            
            # MOVE A PASTA INTEIRA NO DROPBOX
            dbx.files_move_v2(pasta_antiga, nova_pasta[:-1])
            
            nome_arq = caminho_antigo.split('/')[-1]
            post.dropbox_path = f"{nova_pasta}{nome_arq}"
        except Exception as e:
            print(f"Erro Dropbox Move: {e}")

    post.save()
    messages.success(request, "Post movido para a lixeira!")
    return redirect('detalhes_cronograma', pk=post.cronograma.id)

def fazer_upload_dropbox(request, post):
    if post.imagem_preview:
        try:
            dbx_config = DropboxConfig.objects.get(agencia=request.user.minha_agencia)
            dbx = dropbox.Dropbox(
                oauth2_access_token=dbx_config.access_token,
                oauth2_refresh_token=dbx_config.refresh_token,
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET
            )
            caminho = post.gerar_caminho_dropbox().strip()
            nome_arq = post.imagem_preview.name.split('/')[-1]
            full_path = f"/{caminho}{nome_arq}".replace("//", "/")
            file_content = post.imagem_preview.read()
            dbx.files_upload(file_content, full_path, mode=dropbox.files.WriteMode.overwrite)
            post.dropbox_path = full_path
            post.save()
        except Exception as e:
            print(f"ERRO DROPBOX: {str(e)}")

@login_required
def configurar_agencia(request):
    agencia = request.user.minha_agencia
    if request.method == 'POST':
        form = AgenciaForm(request.POST, request.FILES, instance=agencia)
        if form.is_valid():
            redes_data = {}
            for rede_id, nome in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    redes_data[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}'),
                        'usuario': request.POST.get(f'user_{rede_id}'),
                        'senha': request.POST.get(f'pass_{rede_id}')
                    }
            agencia.redes_sociais = redes_data
            form.save()
            messages.success(request, "Agência atualizada!")
            return redirect('configurar_agencia')
    else:
        form = AgenciaForm(instance=agencia)
    return render(request, 'core/configurar_agencia.html', {'form': form, 'agencia': agencia, 'redes_disponiveis': REDES_OPCOES})

@login_required
def conectar_dropbox(request):
    redirect_uri = request.build_absolute_uri('/dropbox-callback/')
    authorize_url = f"https://www.dropbox.com/oauth2/authorize?client_id={settings.DROPBOX_APP_KEY}&response_type=code&token_access_type=offline&redirect_uri={redirect_uri}"
    return redirect(authorize_url)

@login_required
def dropbox_callback(request):
    code = request.GET.get('code')
    token_url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        'code': code, 'grant_type': 'authorization_code',
        'client_id': settings.DROPBOX_APP_KEY, 'client_secret': settings.DROPBOX_APP_SECRET,
        'redirect_uri': request.build_absolute_uri('/dropbox-callback/')
    }
    res = requests.post(token_url, data=data).json()
    if 'access_token' in res:
        DropboxConfig.objects.update_or_create(
            agencia=request.user.minha_agencia,
            defaults={
                'access_token': res['access_token'],
                'refresh_token': res['refresh_token'],
                'expires_at': timezone.now() + timedelta(seconds=res['expires_in'])
            }
        )
        messages.success(request, "Dropbox conectado!")
    return redirect('configurar_agencia')

@login_required
def desconectar_dropbox(request):
    DropboxConfig.objects.filter(agencia=request.user.minha_agencia).delete()
    return redirect('configurar_agencia')

@login_required
def listar_clientes(request):
    clientes = Cliente.objects.filter(agencia=request.user.minha_agencia)
    return render(request, 'core/listar_clientes.html', {'clientes': clientes})

@login_required
def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.agencia = request.user.minha_agencia
            redes_data = {}
            for rede_id, nome in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    redes_data[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}'),
                        'usuario': request.POST.get(f'user_{rede_id}'),
                        'senha': request.POST.get(f'pass_{rede_id}')
                    }
            cliente.redes_sociais = redes_data
            cliente.save()
            messages.success(request, "Cliente cadastrado!")
            return redirect('listar_clientes')
    else:
        form = ClienteForm()
    return render(request, 'core/cadastrar_cliente.html', {'form': form, 'redes_disponiveis': REDES_OPCOES})

def registro_equipe(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect('login')
    return render(request, 'core/registro.html', {'form': UserRegistrationForm()})