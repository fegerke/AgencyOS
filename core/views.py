# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import dropbox
import requests
import base64
import os
from dropbox.files import ThumbnailSize, ThumbnailFormat, PathOrLink
import traceback
from .models import Agencia, Cliente, Post, DropboxConfig, Cronograma, PostArquivo, REDES_OPCOES, Feed, Funcao, Convite
from .forms import AgenciaForm, ClienteForm, PostForm, CronogramaForm, UserRegistrationForm, FeedForm, FuncaoForm, ConviteForm
from .services import upload_file_dropbox
from .utils import gerar_pdf_cronograma 
import threading

# --- DASHBOARD & GERAL ---

@login_required
def home(request):
    agencia = getattr(request.user, 'minha_agencia', None)
    context = {
        'agencia': agencia,
        'total_clientes': Cliente.objects.filter(agencia=agencia).count() if agencia else 0,
        'clientes_recentes': Cliente.objects.filter(agencia=agencia).order_by('-id')[:5] if agencia else [],
    }
    return render(request, 'core/index.html', context)

def registro_equipe(request):
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

# --- FUNÇÕES AUXILIARES DROPBOX ---

def limpar_pastas_vazias_dropbox(dbx, caminho_pasta, limite_pasta):
    try:
        if len(caminho_pasta) <= len(limite_pasta) or not caminho_pasta.startswith(limite_pasta): return
        res = dbx.files_list_folder(caminho_pasta)
        if not res.entries:
            dbx.files_delete_v2(caminho_pasta)
            pasta_pai = "/".join(caminho_pasta.split('/')[:-1])
            limpar_pastas_vazias_dropbox(dbx, pasta_pai, limite_pasta)
    except Exception: pass

def mover_pasta_dropbox(request, post, para_lixeira=True):
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

        dbx.files_move_v2(origem, destino, allow_shared_folder=True, autorename=False)
        for arquivo in post.arquivos.all():
            nome_arquivo = arquivo.dropbox_path.split('/')[-1]
            arquivo.dropbox_path = f"{destino}/{nome_arquivo}"
            arquivo.save()
        pasta_pai_origem = "/".join(origem.split('/')[:-1])
        limpar_pastas_vazias_dropbox(dbx, pasta_pai_origem, limite_limpeza)
    except Exception as e: print(f"Erro ao mover no Dropbox: {e}")

# --- PDF ---

def upload_dropbox_background(user, pdf_bytes, path, cronograma_id):
    """Faz o upload para o Dropbox em segundo plano sem travar o servidor"""
    from .models import Cronograma
    try:
        # Tenta fazer o upload usando sua função original
        link = upload_file_dropbox(user, pdf_bytes, path)
        
        if link:
            # Pega o cronograma fresco do banco e atualiza o link
            cronograma = Cronograma.objects.get(id=cronograma_id)
            cronograma.pdf_dropbox_link = link
            cronograma.pdf_dropbox_path = path
            cronograma.save()
            print(f"Sucesso: PDF {cronograma_id} salvo no Dropbox em background!")
    except Exception as e:
        print(f"Erro no upload em background: {e}")

@login_required
def gerar_pdf_cronograma_view(request, cronograma_id):
    cronograma = get_object_or_404(Cronograma, id=cronograma_id)
    
    try:
        pdf_bytes = gerar_pdf_cronograma(cronograma, request.user)
    except Exception as e:
        print("=== INÍCIO DO ERRO DO PDF ===")
        print(traceback.format_exc())
        print("=== FIM DO ERRO DO PDF ===")
        messages.error(request, f"Erro ao gerar PDF: {e}")
        return redirect('detalhes_cronograma', pk=cronograma.id)

    meses = {
        1:"01 - JANEIRO", 2:"02 - FEVEREIRO", 3:"03 - MARCO", 4:"04 - ABRIL", 
        5:"05 - MAIO", 6:"06 - JUNHO", 7:"07 - JULHO", 8:"08 - AGOSTO", 
        9:"09 - SETEMBRO", 10:"10 - OUTUBRO", 11:"11 - NOVEMBRO", 12:"12 - DEZEMBRO"
    }
    
    cli_slug = slugify(cronograma.cliente.nome_fantasia).replace('-', '_')
    titulo_slug = slugify(cronograma.titulo).replace('-', '_')
    mes_nome = meses.get(cronograma.mes, f"{cronograma.mes:02d}") 
    
    nome_arquivo = f"Cronograma_{cli_slug}_{titulo_slug}.pdf"
    path = f"/AgencyOS/CLIENTES/{cli_slug}/{cronograma.ano}/{mes_nome}/{titulo_slug}/{nome_arquivo}"

    # --- A MÁGICA ACONTECE AQUI ---
    # Inicia o upload em uma Thread separada
    thread = threading.Thread(
        target=upload_dropbox_background, 
        args=(request.user, pdf_bytes, path, cronograma.id)
    )
    thread.start() # Dispara e esquece!
     
    return redirect('detalhes_cronograma', pk=cronograma.id)

@login_required
def visualizar_pdf_cronograma_view(request, cronograma_id):
    cronograma = get_object_or_404(Cronograma, id=cronograma_id)
    if cronograma.pdf_dropbox_link:
        return redirect(cronograma.pdf_dropbox_link)
    else:
        messages.warning(request, "PDF ainda não foi gerado.")
        return redirect('detalhes_cronograma', pk=cronograma.id)

@login_required
def testar_layout_pdf(request, cronograma_id):
    cronograma = get_object_or_404(Cronograma, id=cronograma_id)
    
    try:
        pdf_bytes = gerar_pdf_cronograma(cronograma, request.user)
        
        cli_slug = slugify(cronograma.cliente.nome_fantasia).replace('-', '_')
        titulo_slug = slugify(cronograma.titulo).replace('-', '_')
        nome_arquivo = f"Cronograma_{cli_slug}_{titulo_slug}.pdf"
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
        return response
        
    except Exception as e:
        return HttpResponse(f"<h1>Erro no Laboratório</h1><p>{e}</p>")


# --- CONFIGURAÇÃO AGENCIA ---

@login_required
def configurar_agencia(request):
    agencia = request.user.minha_agencia 
    dbx_config = DropboxConfig.objects.filter(agencia=agencia).first()

    if request.method == 'POST':
        form = AgenciaForm(request.POST, request.FILES, instance=agencia)
        if request.POST.get('limpar_logo') == 'on':
            agencia.logo.delete(save=False)
            agencia.logo = None
            agencia.logo_dropbox_link = None
            
        if form.is_valid():
            agencia_inst = form.save(commit=False)
            
            if 'logo' in request.FILES:
                agencia_inst.save() 
                nome_limpo = slugify(agencia_inst.nome_fantasia)
                extensao = os.path.splitext(agencia_inst.logo.name)[1]
                path_dropbox = f"/AgencyOS/SISTEMA/AGENCIA/{nome_limpo}/LOGO/logo_{nome_limpo}{extensao}"
                
                try:
                    with open(agencia_inst.logo.path, 'rb') as f:
                        link = upload_file_dropbox(request.user, f.read(), path_dropbox)
                        if link: agencia_inst.logo_dropbox_link = link
                except Exception as e: print(f"Erro upload logo agencia: {e}")

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
        'form': form, 'agencia': agencia, 'dbx_config': dbx_config, 'redes_disponiveis': REDES_OPCOES 
    })

# --- CLIENTES ---

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
            for rede_id, _ in REDES_OPCOES:
                if request.POST.get(f'rede_ativa_{rede_id}'):
                    redes_data[rede_id] = {
                        'perfil': request.POST.get(f'url_{rede_id}'),
                        'usuario': request.POST.get(f'user_{rede_id}'),
                        'senha': request.POST.get(f'pass_{rede_id}')
                    }
            cliente.redes_sociais = redes_data
            cliente.save() 
            
            if 'logo' in request.FILES:
                nome_limpo = slugify(cliente.nome_fantasia)
                extensao = os.path.splitext(cliente.logo.name)[1]
                path_dropbox = f"/AgencyOS/SISTEMA/CLIENTES/{nome_limpo}/LOGO/logo_{nome_limpo}{extensao}"
                try:
                    with open(cliente.logo.path, 'rb') as f:
                        link = upload_file_dropbox(request.user, f.read(), path_dropbox)
                        if link:
                            cliente.logo_dropbox_link = link
                            cliente.save()
                except Exception as e: print(f"Erro logo cliente: {e}")

            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('listar_clientes')
    else:
        form = ClienteForm()
    return render(request, 'core/cadastrar_cliente.html', {'form': form, 'redes_disponiveis': REDES_OPCOES})

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

            if 'logo' in request.FILES:
                nome_limpo = slugify(cliente_inst.nome_fantasia)
                extensao = os.path.splitext(cliente_inst.logo.name)[1]
                path_dropbox = f"/AgencyOS/SISTEMA/CLIENTES/{nome_limpo}/LOGO/logo_{nome_limpo}{extensao}"
                try:
                    with open(cliente_inst.logo.path, 'rb') as f:
                        link = upload_file_dropbox(request.user, f.read(), path_dropbox)
                        if link:
                            cliente_inst.logo_dropbox_link = link
                            cliente_inst.save()
                except: pass
            
            messages.success(request, "Cliente atualizado!")
            return redirect('listar_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'core/cadastrar_cliente.html', {'form': form, 'redes_disponiveis': REDES_OPCOES})

@login_required
def excluir_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, agencia=request.user.minha_agencia)
    cliente.delete()
    messages.success(request, f"Cliente removido com sucesso.")
    return redirect('listar_clientes')

@login_required
def gerenciar_funcoes(request, funcao_id=None):
    agencia = request.user.minha_agencia
    
    instancia = get_object_or_404(Funcao, pk=funcao_id, agencia=agencia) if funcao_id else None

    if request.method == 'POST':
        form = FuncaoForm(request.POST, instance=instancia)
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.agencia = agencia
            funcao.save()
            messages.success(request, 'Função salva com sucesso!')
            return redirect('gerenciar_funcoes')
    else:
        form = FuncaoForm(instance=instancia)

    funcoes = Funcao.objects.filter(agencia=agencia)

    context = {
        'form': form,
        'funcoes': funcoes,
    }
    return render(request, 'core/gerenciar_funcoes.html', context)

@login_required
def excluir_funcao(request, funcao_id):
    agencia = request.user.minha_agencia
    funcao = get_object_or_404(Funcao, pk=funcao_id, agencia=agencia)
    
    funcao_nome = funcao.nome
    funcao.delete()
    
    messages.success(request, f'Função "{funcao_nome}" excluída com sucesso!')
    return redirect('gerenciar_funcoes')

@login_required
def gerar_convite(request):
    agencia = request.user.minha_agencia
    link_gerado = None
    convite_obj = None

    if request.method == 'POST':
        form = ConviteForm(request.POST, agencia=agencia)
        if form.is_valid():
            convite = form.save(commit=False)
            convite.agencia = agencia
            convite.save()
            form.save_m2m() 
            
            link_gerado = request.build_absolute_uri(f'/convite/{convite.token}/')
            convite_obj = convite
    else:
        form = ConviteForm(agencia=agencia)

    return render(request, 'core/gerar_convite.html', {
        'form': form, 
        'link_gerado': link_gerado, 
        'convite': convite_obj
    })

# --- CRONOGRAMAS ---

@login_required
def listar_cronogramas(request):
    agencia = request.user.minha_agencia
    clientes = Cliente.objects.filter(agencia=agencia)
    cronogramas = Cronograma.objects.filter(cliente__agencia=agencia, excluido=False)
    
    # 1. Pegando os parâmetros da URL (Filtros)
    cliente_id = request.GET.get('cliente')
    rede_selecionada = request.GET.get('rede')
    mes_selecionado = request.GET.get('mes')
    ano_selecionado = request.GET.get('ano')

    # 2. Aplicando os filtros inteligentes
    if cliente_id:
        cronogramas = cronogramas.filter(cliente_id=cliente_id)
    if rede_selecionada:
        cronogramas = cronogramas.filter(rede_social=rede_selecionada)
    if mes_selecionado:
        cronogramas = cronogramas.filter(mes=mes_selecionado)
    if ano_selecionado:
        cronogramas = cronogramas.filter(ano=ano_selecionado)

    cronogramas = cronogramas.order_by('-id')

    # 3. A Mágica das Cores Dinâmicas
    # Paleta premium de 10 cores. O resto da divisão do ID garante a mesma cor sempre!
    cores_paleta = ['#6c5ce7', '#00b894', '#0984e3', '#e17055', '#e84393', '#fdcb6e', '#00cec9', '#ff9f43', '#f368e0', '#ff6b6b']
    
    for c in cronogramas:
        c.cor_cliente = cores_paleta[c.cliente_id % len(cores_paleta)]
        # Calcula total de posts rapidinho para o badge do card
        c.total_posts = sum(f.posts.filter(excluido=False).count() for f in c.feeds.all())

    # 4. Opções para os selects do Filtro
    meses_opcoes = [(1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'), (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'), (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')]
    anos_opcoes = range(2025, 2030) # Ajuste a margem de anos aqui se precisar

    return render(request, 'core/listar_cronogramas.html', {
        'cronogramas': cronogramas, 
        'clientes': clientes, 
        'cliente_selecionado': int(cliente_id) if cliente_id and cliente_id.isdigit() else '',
        'rede_selecionada': rede_selecionada,
        'mes_selecionado': int(mes_selecionado) if mes_selecionado and mes_selecionado.isdigit() else '',
        'ano_selecionado': int(ano_selecionado) if ano_selecionado and ano_selecionado.isdigit() else '',
        'redes_opcoes': REDES_OPCOES,
        'meses_opcoes': meses_opcoes,
        'anos_opcoes': anos_opcoes,
    })

@login_required
def cadastrar_cronograma(request):
    if request.method == 'POST':
        form = CronogramaForm(request.POST, user=request.user)
        if form.is_valid():
            cronograma = form.save()
            messages.success(request, "Cronograma criado com sucesso!")
            return redirect('detalhes_cronograma', pk=cronograma.id)
    else:
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

    dbx_config = DropboxConfig.objects.filter(agencia=request.user.minha_agencia).first()
    
    if dbx_config:
        try:
            dbx = dropbox.Dropbox(
                oauth2_access_token=dbx_config.access_token,
                oauth2_refresh_token=dbx_config.refresh_token,
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET
            )
            for feed in cronograma.feeds.all():
                for post in feed.posts.filter(excluido=False):
                    arquivo_principal = post.arquivos.first()
                    post.temp_img_url = None
                    post.is_video = False 
                    if arquivo_principal and arquivo_principal.dropbox_path:
                        try:
                            ext = arquivo_principal.dropbox_path.lower()
                            if ext.endswith(('.mp4', '.mov', '.avi', '.m4v')):
                                post.is_video = True
                            post.temp_img_url = dbx.files_get_temporary_link(arquivo_principal.dropbox_path).link
                        except Exception: pass
        except Exception: pass

    return render(request, 'core/detalhes_cronograma.html', {
        'cronograma': cronograma, 'form_cronograma': form_cronograma
    })

@login_required
def excluir_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    agora = timezone.now()
    for feed in cronograma.feeds.all():
        for post in feed.posts.all():
            mover_pasta_dropbox(request, post, para_lixeira=True)
            post.excluido = True
            post.data_exclusao = agora
            post.save()
    cronograma.excluido = True
    cronograma.data_exclusao = agora
    cronograma.save()
    messages.warning(request, "Cronograma movido para a lixeira.")
    return redirect('listar_cronogramas')

@login_required
def recuperar_cronograma(request, pk):
    cronograma = get_object_or_404(Cronograma, pk=pk, cliente__agencia=request.user.minha_agencia)
    for feed in cronograma.feeds.all():
        for post in feed.posts.all():
            mover_pasta_dropbox(request, post, para_lixeira=False)
            post.excluido = False
            post.data_exclusao = None
            post.save()
    cronograma.excluido = False
    cronograma.data_exclusao = None
    cronograma.save()
    messages.success(request, f"Cronograma restaurado!")
    return redirect('lixeira')

# --- FEEDS E POSTS ---

@login_required
def cadastrar_feed(request, cronograma_id):
    cronograma_obj = get_object_or_404(Cronograma, pk=cronograma_id, cliente__agencia=request.user.minha_agencia)
    if request.method == 'POST':
        form = FeedForm(request.POST)
        if form.is_valid():
            feed = form.save(commit=False)
            feed.cronograma = cronograma_obj
            feed.save()
            messages.success(request, "Novo Feed adicionado!")
            return redirect('detalhes_cronograma', pk=cronograma_obj.id)
    else:
        ultimo_feed = cronograma_obj.feeds.order_by('numero').last()
        prox_num = (ultimo_feed.numero + 1) if ultimo_feed else 1
        titulo_sugerido = f"Feed {prox_num:02d}"
        form = FeedForm(initial={'numero': prox_num, 'titulo': titulo_sugerido})
    return render(request, 'core/cadastrar_feed.html', {'form': form, 'cronograma_obj': cronograma_obj})


@login_required
def cadastrar_post(request, feed_id):
    feed_obj = get_object_or_404(Feed, pk=feed_id, cronograma__cliente__agencia=request.user.minha_agencia)
    cronograma_obj = feed_obj.cronograma
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.feed = feed_obj
            post.cronograma = cronograma_obj
            post.save()
            arquivos = request.FILES.getlist('arquivos_multiplos')
            if arquivos:
                for f in arquivos:
                    fazer_upload_dropbox_unico(request, post, f)
            messages.success(request, "Post criado com sucesso!")
            return redirect('detalhes_cronograma', pk=cronograma_obj.id)
    else:
        form = PostForm(initial={'cronograma': cronograma_obj})
    return render(request, 'core/cadastrar_post.html', {'form': form, 'cronograma_obj': cronograma_obj, 'arquivos_existentes': []})

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
            messages.success(request, "Post atualizado com sucesso!")
            return redirect('detalhes_cronograma', pk=cronograma_obj.id)
    else:
        form = PostForm(instance=post)
    
    arquivos_existentes = post.arquivos.all()
    return render(request, 'core/cadastrar_post.html', {'form': form, 'cronograma_obj': cronograma_obj, 'arquivos_existentes': arquivos_existentes})

@login_required
def excluir_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    mover_pasta_dropbox(request, post, para_lixeira=True)
    post.excluido = True
    post.data_exclusao = timezone.now()
    post.save()
    messages.warning(request, "Post movido para a lixeira.")
    return redirect('detalhes_cronograma', pk=post.cronograma.id)

@login_required
def recuperar_post(request, pk):
    post = get_object_or_404(Post, pk=pk, cronograma__cliente__agencia=request.user.minha_agencia)
    mover_pasta_dropbox(request, post, para_lixeira=False)
    post.excluido = False
    post.data_exclusao = None
    post.save()
    messages.success(request, f"Post recuperado!")
    return redirect('lixeira')

@login_required
def excluir_arquivo_post(request, pk):
    arquivo = get_object_or_404(PostArquivo, pk=pk, post__cronograma__cliente__agencia=request.user.minha_agencia)
    post_id = arquivo.post.id
    arquivo.delete()
    messages.success(request, f"Arquivo removido.")
    return redirect('editar_post', pk=post_id)

# --- LIXEIRA & DROPBOX AUTH ---

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
    messages.success(request, "Registros da lixeira removidos.")
    return redirect('lixeira')

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
    except Exception as e: print(f"Erro upload: {e}")

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
        messages.success(request, "Dropbox conectado com sucesso!")
    else: messages.error(request, "Erro ao conectar com o Dropbox.")
    return redirect('configurar_agencia')

@login_required
def desconectar_dropbox(request):
    DropboxConfig.objects.filter(agencia=request.user.minha_agencia).delete()
    messages.info(request, "Dropbox desconectado.")
    return redirect('configurar_agencia')

@login_required
def check_pdf_status(request, cronograma_id):
    cronograma = get_object_or_404(Cronograma, id=cronograma_id)
    return JsonResponse({
        'has_pdf': bool(cronograma.pdf_dropbox_link),
        'pdf_link': cronograma.pdf_dropbox_link if cronograma.pdf_dropbox_link else None
    })

# --- API INTERNA (AJAX) ---
@login_required
def api_get_redes_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id, agencia=request.user.minha_agencia)
    redes_ativas = cliente.redes_sociais.keys()
    
    redes_formatadas = []
    for rede_id, rede_nome in REDES_OPCOES:
        if rede_id in redes_ativas:
            redes_formatadas.append({'id': rede_id, 'nome': rede_nome})
            
    return JsonResponse({'redes': redes_formatadas})