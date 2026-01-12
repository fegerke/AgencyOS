import base64
import dropbox
import requests
import os 
import io
from PIL import Image, ImageOps # Adicionado ImageOps
from django.conf import settings
from django.template.loader import render_to_string
from dropbox.files import ThumbnailSize, ThumbnailFormat, PathOrLink
import weasyprint
from .models import DropboxConfig

def fetch_image_as_base64(url):
    """
    Baixa, CORRIGE ROTAÇÃO, REDIMENSIONA e converte imagem para Base64.
    """
    if not url: return None
    try:
        image_data = None
        
        # 1. Obter os dados brutos
        if url.startswith('http'):
            response = requests.get(url, stream=True)
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
            # --- OTIMIZAÇÃO E CORREÇÃO DE ROTAÇÃO ---
            try:
                # Abre a imagem da memória
                img = Image.open(io.BytesIO(image_data))
                
                # FIX: Aplica a rotação baseada no EXIF (corrige fotos de celular deitadas)
                img = ImageOps.exif_transpose(img)
                
                # Converte para RGB se necessário
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Redimensiona (Economia de RAM)
                max_size = (800, 800)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Salva comprimido
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=70, optimize=True)
                
                image_data = buffer.getvalue()
                mime = "image/jpeg"
            except Exception as e:
                print(f"Aviso: Erro ao processar imagem (usando original): {e}")
                mime = "image/jpeg" if url.lower().endswith(('.jpg', '.jpeg')) else "image/png"

            # Converte para Base64
            b64 = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime};base64,{b64}"
            
    except Exception as e:
        print(f"Erro no fetch_image: {e}")
        pass
    return None

def gerar_pdf_cronograma(cronograma, user):
    
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
    logo_cliente_b64 = None
    if cronograma.cliente.logo_dropbox_link:
        logo_cliente_b64 = fetch_image_as_base64(cronograma.cliente.logo_dropbox_link)
    elif cronograma.cliente.logo:
        logo_cliente_b64 = fetch_image_as_base64(cronograma.cliente.logo.url)

    logo_agencia_b64 = None
    if agencia.logo_dropbox_link:
        logo_agencia_b64 = fetch_image_as_base64(agencia.logo_dropbox_link)
    elif agencia.logo:
        logo_agencia_b64 = fetch_image_as_base64(agencia.logo.url)

    # --- IMAGENS (DROPBOX) ---
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
                            b64 = base64.b64encode(res.content).decode('utf-8')
                            url_data['url'] = f"data:image/png;base64,{b64}"
                        else:
                            url_data['url'] = dbx.files_get_temporary_link(arquivo.dropbox_path).link
                    except: pass
                url_map[post.id] = url_data
        except: pass

    def injetar_url(post):
        d = url_map.get(post.id, {'url': None, 'is_video': False})
        if d['url'] and d['url'].startswith('http') and not d['url'].startswith('data:'):
             post.pdf_img_url = fetch_image_as_base64(d['url'])
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
        'logo_cliente': logo_cliente_b64,
        'logo_agencia': logo_agencia_b64,
        'instagram_cliente': instagram_cliente,
        'instagram_agencia': instagram_agencia,
    })

    pdf_file = weasyprint.HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf()
    return pdf_file