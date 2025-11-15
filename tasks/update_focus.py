#!/usr/bin/env python3
"""
Script para atualizar dados do Boletim Focus
Deve ser executado semanalmente (toda segunda-feira após publicação do Focus)
"""
import sys
import os
from datetime import date, datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import FocusData
from app.focus_scraper import buscar_projecoes_focus, buscar_dados_focus_manual

def main():
    """Função principal para atualizar dados do Focus"""
    env = os.environ.get('FLASK_ENV') or 'default'
    app = create_app(env)
    
    with app.app_context():
        print(f"[{datetime.now()}] Iniciando atualização do Boletim Focus...")
        
        try:
            # Tenta buscar dados do Focus usando método principal
            sucesso = buscar_projecoes_focus()
            
            # Se não funcionou, tenta método alternativo
            if not sucesso:
                print(f"[{datetime.now()}] Tentando método alternativo...")
                sucesso = buscar_dados_focus_manual()
            
            if sucesso:
                print(f"[{datetime.now()}] Dados do Focus atualizados com sucesso!")
            else:
                print(f"[{datetime.now()}] Aviso: Não foi possível atualizar dados do Focus automaticamente.")
                print("Você pode atualizar manualmente através do painel administrativo.")
            
        except Exception as e:
            print(f"[{datetime.now()}] Erro ao atualizar Focus: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    main()

