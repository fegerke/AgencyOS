from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import dropbox
import requests

# Importação de todos os modelos e formulários necessários
from .models import Agencia, Cliente, Post, DropboxConfig, Cronograma, PostArquivo, REDES_OPCOES
from .forms import AgenciaForm, ClienteForm, PostForm, CronogramaForm, UserRegistrationForm

# --- DASHBOARD & GERAL ---

@login_required
def home(request):
    """Página inicial com resumo de métricas."""
    agencia = getattr(request.user, 'minha_agencia', None)
    context = {
        'agencia': agencia,
        'total_clientes': Cliente.objects.filter(agencia=agencia).count() if agencia else 0,
        'clientes_recentes': Cliente.objects.filter(agencia=agencia).order_by('-id')[:5] if agencia else [],
    }
    return render(request, 'core/index.html', context)

def registro_equipe(request):
    """Cadastro de novos usuários/colaboradores."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Usuário registrado com sucesso!")
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

# --- FUNÇÕES AUXILIARES DROPBOX (LIMPEZA E MOVIMENTAÇÃO) ---

def limpar_pastas_vazias_dropbox(dbx, caminho_pasta, limite_pasta):
    """
    Sobe o nível das pastas a partir de caminho_pasta e deleta se estiverem vazias.
    Para ao chegar em limite_pasta.
    """
    try:
        # Garante que não estamos tentando mexer na raiz ou fora do limite
        if len(caminho_pasta) <= len(limite_pasta) or not caminho_pasta.startswith(limite_pasta):
            return

        # Tenta listar o conteúdo da pasta
        res = dbx.files_list_folder(caminho_pasta)
        
        # Se não houver entradas, a pasta está vazia
        if not res.entries:
            dbx.files_delete_v2(caminho_pasta)
            print(f"Pasta vazia removida: {caminho_pasta}")
            
            # Sobe um nível e chama a função recursivamente
            pasta_pai = "/".join(caminho_pasta.split('/')[:-1])
            limpar_pastas_vazias_dropbox(dbx, pasta_pai, limite_pasta)
            
    except Exception as e:
        print(f"Informativo: Parou limpeza de pastas em {caminho_pasta}. (Motivo: {e})")

def mover_pasta_dropbox(request, post, para_lixeira=True):
    """
    Move a pasta do post entre CLIENTES e LIXEIRA no Dropbox e limpa caminhos vazios.
    """
    try:
        dbx_config = DropboxConfig.objects.get(agencia=request.user.minha_agencia)
        dbx = dropbox.Dropbox(
            oauth2_access_token=dbx_config.access_token,
            oauth2_refresh_token=dbx_config.refresh_token,
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET
        )

        cliente = post.cronograma.cliente.nome_fantasia
        ano = str(post.cronograma.ano)
        meses = {1:"01 - JANEIRO", 2:"02 - FEVEREIRO", 3:"03 - MARCO", 4:"04 - ABRIL", 5:"05 - MAIO", 6:"06 - JUNHO", 7:"07 - JULHO", 8:"08 - AGOSTO", 9:"09 - SETEMBRO", 10:"10 - OUTUBRO", 11:"11 - NOVEMBRO", 12:"12 - DEZEMBRO"}
        mes_nome = meses.get(post.cronograma.mes)
        
        caminho_comum = f"{cliente}/{ano}/{mes_nome}/{post.cronograma.titulo}/{post.titulo}"
        
        if para_lixeira:
            origem = f"/AgencyOS/CLIENTES/{caminho_comum}"
            destino = f"/AgencyOS/LIXEIRA/CLIENTES/{caminho_comum}"
            limite_limpeza = "/AgencyOS/CLIENTES"
        else:
            origem = f"/AgencyOS/LIXEIRA/CLIENTES/{caminho_comum}"
            destino = f"/AgencyOS/CLIENTES/{caminho_comum}"
            limite_limpeza = "/AgencyOS/LIXEIRA/CLIENTES"

        # 1. Move a pasta do post
        dbx.files_move_v2(origem, destino, allow_shared_folder=True, autorename=False)
        
        # 2. Atualiza os arquivos no banco
        for arquivo in post.arquivos.all():
            nome_arquivo = arquivo.dropbox_path.split('/')[-1]
            arquivo.dropbox_path = f"{destino}/{nome_arquivo}"
            arquivo.save()

        # 3. Limpeza de pastas vazias no local de origem
        pasta_pai_origem = "/".join(origem.split('/')[:-1])
        limpar_pastas_vazias_dropbox(dbx, pasta_pai_origem, limite_limpeza)

    except Exception as e:
        print(f"Erro ao mover no Dropbox: {e}")

# --- CLIENTES / AGENCIA ---

@login_required
def configurar_agencia(request):
    agencia = request.user.minha_agencia 
    dbx_config = DropboxConfig.objects.filter(agencia=agencia).first()

    if request.method == 'POST':
        form = AgenciaForm(request.POST, request.FILES, instance=agencia)
        
        # --- LÓGICA PARA APAGAR LOGO ---
        # Se o checkbox "limpar_logo" vier marcado, deletamos o arquivo
        if request.POST.get('limpar_logo') == 'on':
            agencia.logo.delete(save=False) # Deleta arquivo físico
            agencia.logo = None # Limpa referência no banco
            
        if form.is_valid():
            agencia_inst = form.save(commit=False)
            
            # Lógica das redes sociais (Mantida)
            novas_redes = {}
            for rede_id, rede_nome in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    novas_redes[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}', ''),
                        'usuario': request.POST.get(f'user_{rede_id}', ''),
                        'senha': request.POST.get(f'pass_{rede_id}', ''),
                    }
            agencia_inst.redes_sociais = novas_redes
            agencia_inst.save()
            
            messages.success(request, "Configurações atualizadas!")
            return redirect('configurar_agencia')
    else:
        form = AgenciaForm(instance=agencia)

    return render(request, 'core/configurar_agencia.html', {
        'form': form,
        'agencia': agencia,
        'dbx_config': dbx_config,
        'redes_disponiveis': REDES_OPCOES 
    })

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
            # Lógica para salvar o JSON de redes_sociais (conforme discutido anteriormente)
            redes_data = {}
            for rede_id, _ in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    redes_data[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}'),
                        'usuario': request.POST.get(f'user_{rede_id}'),
                        'senha': request.POST.get(f'pass_{rede_id}')
                    }
            cliente.redes_sociais = redes_data
            cliente.save()
            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('listar_clientes')
    else:
        form = ClienteForm()
    
    # IMPORTANTE: Passar 'redes_disponiveis' para o loop no HTML
    return render(request, 'core/cadastrar_cliente.html', {
        'form': form, 
        'redes_disponiveis': REDES_OPCOES
    })

@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, agencia=request.user.minha_agencia)
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=cliente)
        if form.is_valid():
            cliente_inst = form.save(commit=False)
            redes_data = {}
            for rede_id, _ in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    redes_data[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}'),
                        'usuario': request.POST.get(f'user_{rede_id}'),
                        'senha': request.POST.get(f'pass_{rede_id}')
                    }
            cliente_inst.redes_sociais = redes_data
            cliente_inst.save()
            messages.success(request, "Cliente atualizado!")
            return redirect('listar_clientes')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'core/cadastrar_cliente.html', {
        'form': form, 
        'redes_disponiveis': REDES_OPCOES
    })

@login_required
def excluir_cliente(request, pk):
    """Exclui o cliente da agência logada."""
    cliente = get_object_or_404(Cliente, pk=pk, agencia=request.user.minha_agencia)
    nome = cliente.nome_fantasia
    cliente.delete()
    messages.success(request, f"Cliente {nome} removido com sucesso.")
    return redirect('listar_clientes')

# --- CRONOGRAMAS ---

@login_required
def listar_cronogramas(request):
    """Exibe cronogramas com filtro por cliente."""
    agencia = request.user.minha_agencia
    cliente_id = request.GET.get('cliente')
    
    # Busca todos os clientes para preencher o seletor do filtro no HTML
    clientes = Cliente.objects.filter(agencia=agencia)
    
    # Base da query de cronogramas ativos
    cronogramas = Cronograma.objects.filter(cliente__agencia=agencia, excluido=False)
    
    # Aplica o filtro se um cliente específico foi selecionado no dropdown
    if cliente_id:
        cronogramas = cronogramas.filter(cliente_id=cliente_id)
    
    # Ordenação padrão pelos mais recentes
    cronogramas = cronogramas.order_by('-id')
    
    return render(request, 'core/listar_cronogramas.html', {
        'cronogramas': cronogramas,
        'clientes': clientes,
        'cliente_selecionado': int(cliente_id) if cliente_id and cliente_id.isdigit() else None
    })

@login_required
def cadastrar_cronograma(request):
    """Cria cronograma passando o usuário logado para o Form."""
    if request.method == 'POST':
        form = CronogramaForm(request.POST, user=request.user)
        if form.is_valid():
            cronograma = form.save()
            messages.success(request, "Cronograma criado com sucesso!")
            return redirect('detalhes_cronograma', pk=cronograma.id)
    else:
        # Passamos 'user' para o Form filtrar os clientes da agência
        form = CronogramaForm(user=request.user)
    
    return render(request, 'core/cadastrar_cronograma.html', {'form': form})

@login_required
def detalhes_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    
    if request.method == 'POST' and 'editar_cronograma' in request.POST:
        form_cronograma = CronogramaForm(request.POST, instance=cronograma, user=request.user)
        if form_cronograma.is_valid():
            form_cronograma.save()
            messages.success(request, "Cronograma atualizado!")
            return redirect('detalhes_cronograma', pk=pk)
    else:
        form_cronograma = CronogramaForm(instance=cronograma, user=request.user)

    posts = cronograma.posts.filter(excluido=False).order_by('data_publicacao')

    # LÓGICA DROPBOX COM DETECÇÃO DE VÍDEO
    dbx_config = DropboxConfig.objects.filter(agencia=request.user.minha_agencia).first()
    
    if dbx_config:
        try:
            dbx = dropbox.Dropbox(
                oauth2_access_token=dbx_config.access_token,
                oauth2_refresh_token=dbx_config.refresh_token,
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET
            )
            
            for post in posts:
                arquivo_principal = post.arquivos.first()
                post.temp_img_url = None
                post.is_video = False # Flag para o HTML saber o que renderizar

                if arquivo_principal and arquivo_principal.dropbox_path:
                    try:
                        # Verifica extensão para decidir se é video
                        ext = arquivo_principal.dropbox_path.lower()
                        if ext.endswith(('.mp4', '.mov', '.avi', '.m4v')):
                            post.is_video = True
                        
                        post.temp_img_url = dbx.files_get_temporary_link(arquivo_principal.dropbox_path).link
                    except Exception as e:
                        print(f"Erro link temp: {e}")
        except Exception as e:
            print(f"Erro conexão Dropbox: {e}")

    return render(request, 'core/detalhes_cronograma.html', {
        'cronograma': cronograma,
        'posts': posts,
        'form_cronograma': form_cronograma
    })

@login_required
def excluir_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    agora = timezone.now()
    
    # 1. Move cada post (isso limpa as pastas vazias no Dropbox automaticamente)
    for post in cronograma.posts.all():
        mover_pasta_dropbox(request, post, para_lixeira=True)
    
    # 2. Soft delete no banco
    cronograma.excluido = True
    cronograma.data_exclusao = agora
    cronograma.posts.all().update(excluido=True, data_exclusao=agora)
    cronograma.save()
    
    messages.warning(request, "Cronograma movido para a lixeira.")
    return redirect('listar_cronogramas')

@login_required
def recuperar_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    
    # Move todos os posts de volta para CLIENTES
    for post in cronograma.posts.all():
        mover_pasta_dropbox(request, post, para_lixeira=False)
        
    cronograma.excluido = False
    cronograma.data_exclusao = None
    cronograma.save()
    cronograma.posts.all().update(excluido=False, data_exclusao=None)
    
    messages.success(request, f"Cronograma '{cronograma.titulo}' restaurado!")
    return redirect('lixeira')

# --- POSTS ---

@login_required
def cadastrar_post(request):
    cronograma_id = request.GET.get('cronograma')
    cronograma_obj = get_object_or_404(Cronograma, pk=cronograma_id, cliente__agencia=request.user.minha_agencia)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save()
            arquivos = request.FILES.getlist('arquivos_multiplos')
            if arquivos:
                for f in arquivos:
                    fazer_upload_dropbox_unico(request, post, f)
            
            # SUCESSO! Redireciona de volta para o CRONOGRAMA
            messages.success(request, "Post criado com sucesso!")
            return redirect('detalhes_cronograma', pk=cronograma_obj.id)
    else:
        form = PostForm(initial={'cronograma': cronograma_obj})
        
    return render(request, 'core/cadastrar_post.html', {
        'form': form, 
        'cronograma_obj': cronograma_obj,
        'arquivos_existentes': [] 
    })

@login_required
def editar_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    cronograma_obj = post.cronograma
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            arquivos = request.FILES.getlist('arquivos_multiplos')
            if arquivos:
                for f in arquivos:
                    fazer_upload_dropbox_unico(request, post, f)
            
            # SUCESSO! Redireciona de volta para o CRONOGRAMA
            messages.success(request, "Post atualizado com sucesso!")
            return redirect('detalhes_cronograma', pk=cronograma_obj.id)
    else:
        form = PostForm(instance=post)

    # --- LÓGICA DE PREVIEW ---
    arquivos_existentes = post.arquivos.all()
    dbx_config = DropboxConfig.objects.filter(agencia=request.user.minha_agencia).first()
    
    if dbx_config:
        try:
            dbx = dropbox.Dropbox(
                oauth2_access_token=dbx_config.access_token,
                oauth2_refresh_token=dbx_config.refresh_token,
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET
            )
            for arq in arquivos_existentes:
                arq.temp_url = None
                arq.is_video = False
                if arq.dropbox_path:
                    try:
                        ext = arq.dropbox_path.lower()
                        if ext.endswith(('.mp4', '.mov', '.avi', '.m4v')):
                            arq.is_video = True
                        arq.temp_url = dbx.files_get_temporary_link(arq.dropbox_path).link
                    except Exception:
                        pass
        except Exception:
            pass
        
    return render(request, 'core/cadastrar_post.html', {
        'form': form, 
        'cronograma_obj': cronograma_obj,
        'arquivos_existentes': arquivos_existentes 
    })

@login_required
def excluir_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    
    # Move no Dropbox e limpa pastas
    mover_pasta_dropbox(request, post, para_lixeira=True)
    
    # Soft delete no banco
    post.excluido = True
    post.data_exclusao = timezone.now()
    post.save()
    
    messages.warning(request, "Post movido para a lixeira.")
    return redirect('detalhes_cronograma', pk=post.cronograma.id)

@login_required
def recuperar_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    
    # Traz de volta no Dropbox
    mover_pasta_dropbox(request, post, para_lixeira=False)
    
    post.excluido = False
    post.data_exclusao = None
    post.save()
    
    messages.success(request, f"Post '{post.titulo}' recuperado!")
    return redirect('lixeira')

@login_required
def excluir_arquivo_post(request, pk):
    arquivo = get_object_or_404(PostArquivo, pk=pk, post__cronograma__cliente__agencia=request.user.minha_agencia)
    post_id = arquivo.post.id
    
    # Opcional: Deletar do Dropbox também se quiser
    # Por segurança, vou apenas deletar do banco por enquanto para não perder originais sem querer
    # Se quiser deletar do Dropbox, precisaria instanciar o cliente dbx aqui e chamar files_delete_v2
    
    nome = arquivo.arquivo.name
    arquivo.delete()
    messages.success(request, f"Arquivo removido.")
    return redirect('editar_post', pk=post_id)

# --- LIXEIRA ---

@login_required
def lixeira(request):
    agencia = request.user.minha_agencia
    posts_excluidos = Post.objects.filter(cronograma__cliente__agencia=agencia, excluido=True).order_by('-data_exclusao')
    cronogramas_excluidos = Cronograma.objects.filter(cliente__agencia=agencia, excluido=True).order_by('-data_exclusao')
    return render(request, 'core/lixeira.html', {'posts': posts_excluidos, 'cronogramas': cronogramas_excluidos})

@login_required
def limpar_lixeira_total(request):
    agencia = request.user.minha_agencia
    Post.objects.filter(cronograma__cliente__agencia=agencia, excluido=True).delete()
    Cronograma.objects.filter(cliente__agencia=agencia, excluido=True).delete()
    messages.success(request, "Registros da lixeira removidos do sistema.")
    return redirect('lixeira')

# --- UPLOAD E CONFIGURAÇÃO DROPBOX ---

def fazer_upload_dropbox_unico(request, post, arquivo):
    try:
        dbx_config = DropboxConfig.objects.get(agencia=request.user.minha_agencia)
        dbx = dropbox.Dropbox(
            oauth2_access_token=dbx_config.access_token,
            oauth2_refresh_token=dbx_config.refresh_token,
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET
        )

        cliente = post.cronograma.cliente.nome_fantasia
        ano = str(post.cronograma.ano)
        meses = {1:"01 - JANEIRO", 2:"02 - FEVEREIRO", 3:"03 - MARCO", 4:"04 - ABRIL", 5:"05 - MAIO", 6:"06 - JUNHO", 7:"07 - JULHO", 8:"08 - AGOSTO", 9:"09 - SETEMBRO", 10:"10 - OUTUBRO", 11:"11 - NOVEMBRO", 12:"12 - DEZEMBRO"}
        mes_nome = meses.get(post.cronograma.mes)
        
        caminho_dropbox = f"/AgencyOS/CLIENTES/{cliente}/{ano}/{mes_nome}/{post.cronograma.titulo}/{post.titulo}/{arquivo.name}"
        
        dbx.files_upload(arquivo.read(), caminho_dropbox, mode=dropbox.files.WriteMode.overwrite)
        
        PostArquivo.objects.create(post=post, dropbox_path=caminho_dropbox)
    except Exception as e:
        print(f"Erro upload: {e}")

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
        'code': code, 
        'grant_type': 'authorization_code',
        'client_id': settings.DROPBOX_APP_KEY, 
        'client_secret': settings.DROPBOX_APP_SECRET,
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
        messages.success(request, "Dropbox conectado com sucesso!")
    else:
        messages.error(request, "Erro ao conectar com o Dropbox.")
        
    return redirect('configurar_agencia')

@login_required
def desconectar_dropbox(request):
    DropboxConfig.objects.filter(agencia=request.user.minha_agencia).delete()
    messages.info(request, "Dropbox desconectado.")
    return redirect('configurar_agencia')