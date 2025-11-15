import os
from datetime import timedelta

class Config:
    """Configuração base da aplicação"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///comparador.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ACCESS_CODE_DEFAULT = os.environ.get('ACCESS_CODE_DEFAULT') or 'REALIZAR-1A73'
    if os.environ.get('ADMIN_EMAILS'):
        ADMIN_EMAILS = [email.strip() for email in os.environ.get('ADMIN_EMAILS', '').split(',') if email.strip()]
    else:
        ADMIN_EMAILS = ['suellencna@gmail.com']
    
    # Configurações de acesso
    ACCESS_CODE_VALIDITY_DAYS = 365  # 1 ano
    
    # Configurações de atualização do Focus
    FOCUS_UPDATE_DAY = 1  # Segunda-feira (0=Monday)
    FOCUS_UPDATE_TIME = '09:00'  # 9h da manhã
    
    # Configurações do BCB
    BCB_FOCUS_URL = 'https://www.bcb.gov.br/publicacoes/focus'
    BCB_FOCUS_EMAIL = 'focus@bcb.gov.br'
    
    # Configurações de cálculo
    CUSTODIA_TESOURO_ANUAL = 0.002  # 0,2% ao ano
    SELIC_TAX = 0.10  # Taxa aproximada CDI = Selic - 0,10%

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///comparador.db'

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # PostgreSQL no Render
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}




