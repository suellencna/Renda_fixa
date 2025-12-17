"""
Funções auxiliares
"""
import secrets
import string

def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_porcentagem(valor, casas=2):
    """Formata valor como porcentagem"""
    return f"{valor:.{casas}f}%"

def gerar_codigo_acesso(prefixo="POTENS"):
    """
    Gera código de acesso único no formato PREFIXO-XXXX-XXXX
    """
    # Gera 8 caracteres alfanuméricos
    caracteres = string.ascii_uppercase + string.digits
    codigo_aleatorio = ''.join(secrets.choice(caracteres) for _ in range(8))
    
    # Formata: PREFIXO-XXXX-XXXX
    codigo = f"{prefixo}-{codigo_aleatorio[:4]}-{codigo_aleatorio[4:]}"
    
    return codigo

def validar_codigo_formato(codigo):
    """Valida formato do código de acesso"""
    # Formato: PREFIXO-XXXX-XXXX
    pattern = r'^[A-Z]+-\w{4}-\w{4}$'
    import re
    return bool(re.match(pattern, codigo.upper()))






