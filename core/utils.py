import base64
import dropbox
import requests
import os 
import io
import tempfile
import gc
from PIL import Image, ImageOps
from django.conf import settings
from django.template.loader import render_to_string
from dropbox.files import ThumbnailSize, ThumbnailFormat, PathOrLink
import weasyprint
from .models import DropboxConfig

def process_image_to_temp_file(url, temp_file_list):
    """
    Baixa, corrige rotação, redimensiona e salva em arquivo temporário no disco.
    Retorna o caminho do arquivo (file://...) para o WeasyPrint usar.
    Adiciona o caminho na lista temp_file_list para limpeza posterior.
    """
    if not url: return None
    
    try:
        image_data = None
        
        # 1. Download (Stream) ou Leitura Local
        if url.startswith('http'):
            # Timeout para não travar o worker
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                image_data = response.content
        else:
            clean_path = url.lstrip('/')
            if clean_path.startswith('media/'):
                file_path = os.path.join(settings.BASE_DIR, clean_path)
            else:
                file_path = os.path.join(settings.MEDIA_ROOT, clean_path)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    image_data = f.read()
        
        if image_data:
            # 2. Processamento com PIL
            img = Image.open(io.BytesIO(image_data))
            
            # Corrige rotação (EXIF)
            img = ImageOps.exif_transpose(img)
            
            # Converte para RGB
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Redimensiona (550px é suficiente para a grade e economiza muito)
            max_size = (550, 550)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 3. Salva em Arquivo Temporário
            # delete=False pois precisamos fechar o arquivo para o WeasyPrint abrir depois
            t = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(t, format='JPEG', quality=65, optimize=True)
            t.close()
            
            # Registra para deletar depois
            temp_file_list.append(t.name)
            
            # Retorna path absoluto para o template
            return f"file://{t.name}"
            
    except Exception as e:
        print(f"Erro processando imagem {url}: {e}")
        return None
    
    return None

# Mantido para retrocompatibilidade se algo externo usar (opcional)
def fetch_image_as_base64(url):
    return None 

def gerar_pdf_cronograma(cronograma, user):
    
    # Lista para rastrear arquivos temporários criados
    temp_resources = []
    
    try:
        todos_posts = cronograma.posts.filter(excluido=False).order_by('data_publicacao')
        agencia = cronograma.cliente.agencia

        # --- TRATAMENTO DE HANDLES ---
        def get_handle(obj):
            redes = obj.redes_sociais.get('instagram', {})
            val = redes.get('perfil') or redes.get('usuario') or ""
            if not val: return ""
            if 'instagram.com/' in val:
                val = val.split('instagram.com/')[-1].replace('/', '')
            val = val.strip().lower().replace(' ', '_')
            if not val.startswith('@'): return f"@{val}"
            return val

        instagram_cliente = get_handle(cronograma.cliente)
        if not instagram_cliente: 
            nome_limpo = cronograma.cliente.nome_fantasia.strip().lower().replace(' ', '_')
            instagram_cliente = f"@{nome_limpo}"

        instagram_agencia = get_handle(agencia)
        if not instagram_agencia: 
            nome_limpo = agencia.nome_fantasia.strip().lower().replace(' ', '_')
            instagram_agencia = f"@{nome_limpo}"

        # --- LOGOS (Para disco) ---
        logo_cliente_path = None
        if cronograma.cliente.logo_dropbox_link:
            logo_cliente_path = process_image_to_temp_file(cronograma.cliente.logo_dropbox_link, temp_resources)
        elif cronograma.cliente.logo:
            logo_cliente_path = process_image_to_temp_file(cronograma.cliente.logo.url, temp_resources)

        logo_agencia_path = None
        if agencia.logo_dropbox_link:
            logo_agencia_path = process_image_to_temp_file(agencia.logo_dropbox_link, temp_resources)
        elif agencia.logo:
            logo_agencia_path = process_image_to_temp_file(agencia.logo.url, temp_resources)

        # --- IMAGENS DROPBOX ---
        url_map = {} 
        dbx_config = DropboxConfig.objects.filter(agencia=agencia).first()
        
        if dbx_config:
            try:
                dbx = dropbox.Dropbox(
                    oauth2_access_token=dbx_config.access_token, 
                    oauth2_refresh_token=dbx_config.refresh_token, 
                    app_key=settings.DROPBOX_APP_KEY, 
                    app_secret=settings.DROPBOX_APP_SECRET
                )
                for post in todos_posts:
                    url_data = {'url': None, 'is_video': False}
                    arquivo = post.arquivos.first()
                    if arquivo and arquivo.dropbox_path:
                        try:
                            ext = arquivo.dropbox_path.lower()
                            is_video = ext.endswith(('.mp4', '.mov', '.avi', '.m4v'))
                            url_data['is_video'] = is_video
                            if is_video:
                                # Vídeo: Pega thumb
                                _, res = dbx.files_get_thumbnail_v2(
                                    resource=PathOrLink.path(arquivo.dropbox_path), 
                                    format=ThumbnailFormat.png, size=ThumbnailSize.w640h480
                                )
                                # Salva thumb em disco direto
                                t = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                                t.write(res.content)
                                t.close()
                                temp_resources.append(t.name)
                                url_data['url'] = f"file://{t.name}"
                            else:
                                # Imagem: Link temp para baixar depois
                                url_data['url'] = dbx.files_get_temporary_link(arquivo.dropbox_path).link
                        except: pass
                    url_map[post.id] = url_data
            except: pass

        def injetar_url(post):
            d = url_map.get(post.id, {'url': None, 'is_video': False})
            
            # Se for URL http, processa e salva no disco. Se já for file://, mantém.
            if d['url'] and d['url'].startswith('http'):
                post.pdf_img_url = process_image_to_temp_file(d['url'], temp_resources)
            else:
                post.pdf_img_url = d['url']
                
            post.is_video = d['is_video']

        # --- MONTAGEM ---
        lotes_renderizacao = []
        lista_completa = list(todos_posts)
        
        for i in range(0, len(lista_completa), 9):
            lote_atual = lista_completa[i:i+9]
            for p in lote_atual: injetar_url(p)
                
            grade_visual = lote_atual[::-1]
            trincas_do_lote = []
            for j in range(0, len(lote_atual), 3):
                trincas_do_lote.append(lote_atual[j:j+3][::-1])
                
            numero_pagina = (i // 9) + 1
            titulo_grade = cronograma.titulo if numero_pagina == 1 else f"{cronograma.titulo} - Pág {numero_pagina:02d}"

            lotes_renderizacao.append({
                'posts_grade': grade_visual,
                'trincas': trincas_do_lote,
                'titulo_grade': titulo_grade
            })

        # --- RENDERIZA ---
        html_string = render_to_string('core/pdf_cronograma.html', {
            'cronograma': cronograma,
            'lotes': lotes_renderizacao,
            'agencia': agencia,
            'logo_cliente': logo_cliente_path, # Agora é path, não b64
            'logo_agencia': logo_agencia_path, # Agora é path, não b64
            'instagram_cliente': instagram_cliente,
            'instagram_agencia': instagram_agencia,
        })

        # Gera PDF
        pdf_file = weasyprint.HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
        return pdf_file

    finally:
        # --- LIMPEZA CRÍTICA ---
        # Apaga todos os arquivos temporários do disco
        for path in temp_resources:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except: pass
        
        # Força coleta de lixo do Python
        gc.collect()