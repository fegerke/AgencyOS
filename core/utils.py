import base64
import dropbox
import requests
import os 
import io
import tempfile
import gc
import pathlib
from PIL import Image, ImageOps
from django.conf import settings
from django.template.loader import render_to_string
from dropbox.files import ThumbnailSize, ThumbnailFormat, PathOrLink
import weasyprint
from weasyprint.text.fonts import FontConfiguration 
from .models import DropboxConfig

def process_image_to_temp_file(url, temp_file_list):
    """
    Baixa, corrige rotação, redimensiona e salva em arquivo temporário no disco.
    Retorna a URI do arquivo.
    """
    if not url: return None
    
    try:
        image_data = None
        
        if url.startswith('http'):
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
            img = Image.open(io.BytesIO(image_data))
            img = ImageOps.exif_transpose(img)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 550px é suficiente para a grade e economiza RAM no Render
            max_size = (300, 300)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            t = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            img.save(t, format='JPEG', quality=50, optimize=True)
            t.close()
            
            temp_file_list.append(t.name)
            return pathlib.Path(t.name).as_uri()
            
    except Exception as e:
        print(f"Erro processando imagem {url}: {e}")
        return None
    
    return None

def fetch_image_as_base64(url):
    return None 

def gerar_pdf_cronograma(cronograma, user):
    """
    Gera o PDF do cronograma usando WeasyPrint com suporte a fontes personalizadas.
    """
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

        # --- LOGOS ---
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
                                _, res = dbx.files_get_thumbnail_v2(
                                    resource=PathOrLink.path(arquivo.dropbox_path), 
                                    format=ThumbnailFormat.png, size=ThumbnailSize.w640h480
                                )
                                t = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                                t.write(res.content)
                                t.close()
                                temp_resources.append(t.name)
                                url_data['url'] = pathlib.Path(t.name).as_uri()
                            else:
                                url_data['url'] = dbx.files_get_temporary_link(arquivo.dropbox_path).link
                        except: pass
                    url_map[post.id] = url_data
            except: pass

        def injetar_url(post):
            d = url_map.get(post.id, {'url': None, 'is_video': False})
            if d['url'] and d['url'].startswith('http'):
                post.pdf_img_url = process_image_to_temp_file(d['url'], temp_resources)
            else:
                post.pdf_img_url = d['url']
            post.is_video = d['is_video']

        # --- MONTAGEM DOS LOTES ---
        lotes_renderizacao = []
        feeds_cadastrados = cronograma.feeds.all().order_by('numero')
        
        for feed in feeds_cadastrados:
            posts_do_feed = list(feed.posts.filter(excluido=False).order_by('data_publicacao'))
            if not posts_do_feed: continue
                
            for p in posts_do_feed: injetar_url(p)
                
            grade_visual = posts_do_feed[::-1]
            trincas_do_lote = []
            for j in range(0, len(posts_do_feed), 3):
                trincas_do_lote.append(posts_do_feed[j:j+3][::-1])
                
            titulo_grade = feed.titulo or f"Feed {feed.numero:02d}"

            lotes_renderizacao.append({
                'posts_grade': grade_visual,
                'trincas': trincas_do_lote,
                'titulo_grade': titulo_grade
            })

        # --- RENDERIZAÇÃO HTML ---
        html_string = render_to_string('core/pdf_cronograma.html', {
            'cronograma': cronograma,
            'lotes': lotes_renderizacao,
            'agencia': agencia,
            'logo_cliente': logo_cliente_path, 
            'logo_agencia': logo_agencia_path, 
            'instagram_cliente': instagram_cliente,
            'instagram_agencia': instagram_agencia,
            'base_dir': settings.BASE_DIR,
        })

        # --- GERAÇÃO DO PDF (VERSÃO ROBUSTA E CORRIGIDA) ---
        font_config = FontConfiguration()
        
        # 1. Cria a instância do HTML (ESSA LINHA QUE FALTAVA)
        html_obj = weasyprint.HTML(
            string=html_string, 
            base_url=str(settings.BASE_DIR)
        )

        # 2. Renderiza o layout aplicando as fontes
        documento_renderizado = html_obj.render(font_config=font_config)

        # 3. Escreve o PDF sem tentar re-aplicar configurações conflitantes
        pdf_file = documento_renderizado.write_pdf(optimize_images=False)
        
        return pdf_file

    finally:
        # Limpeza de arquivos temporários para não encher o disco do servidor
        for path in temp_resources:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except: pass
        gc.collect()