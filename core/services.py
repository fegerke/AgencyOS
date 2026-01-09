# core/services.py
import dropbox
from django.conf import settings
from .models import Agencia

def get_dbx_client(user):
    """Tenta obter o cliente Dropbox da Agência do usuário"""
    try:
        agencia = user.minha_agencia
        if not agencia or not hasattr(agencia, 'dropbox_config'):
            return None
        
        config = agencia.dropbox_config
        return dropbox.Dropbox(
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET,
            oauth2_refresh_token=config.refresh_token
        )
    except Exception as e:
        print(f"Erro ao conectar Dropbox: {e}")
        return None

def upload_file_dropbox(user, file_bytes, dropbox_path):
    """
    Faz upload de bytes para o Dropbox e retorna o Link DIRETO (raw=1).
    Isso permite que o navegador abra o arquivo em vez de ir para a tela de download do Dropbox.
    """
    dbx = get_dbx_client(user)
    if not dbx:
        return None

    try:
        # Upload (mode overwrite para substituir arquivo se já existir)
        dbx.files_upload(file_bytes, dropbox_path, mode=dropbox.files.WriteMode.overwrite)
        
        # Criar ou pegar link compartilhado
        try:
            link_meta = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            url = link_meta.url
        except dropbox.exceptions.ApiError as e:
            # Se já existe link, pega o existente
            if e.error.is_shared_link_already_exists():
                links = dbx.sharing_list_shared_links(path=dropbox_path).links
                url = links[0].url if links else None
            else:
                raise e
        
        # O TRUQUE: Substituir dl=0 por raw=1
        if url:
            url = url.replace("?dl=0", "?raw=1").replace("&dl=0", "&raw=1")
            
        return url
        
    except Exception as e:
        print(f"Erro no Upload Dropbox: {e}")
        return None

def get_temporary_link_for_image(user, dropbox_path):
    """
    Pega um link temporário direto para baixar a imagem (usado pelo PDF Generator)
    """
    dbx = get_dbx_client(user)
    if not dbx or not dropbox_path: return None
    
    try:
        link = dbx.files_get_temporary_link(dropbox_path)
        return link.link
    except:
        return None