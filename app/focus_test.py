"""
Script de teste para verificar se a API do BCB está funcionando
Execute: python -m app.focus_test
"""
from app import create_app, db
from app.focus_scraper import buscar_projecoes_focus, buscar_dados_focus_manual
from datetime import datetime

def test_api():
    """Testa a conexão com a API do BCB"""
    app = create_app('development')
    
    with app.app_context():
        print("=" * 60)
        print("TESTE DE CONEXÃO COM API DO BCB - BOLETIM FOCUS")
        print("=" * 60)
        print()
        
        # Verifica se a biblioteca está instalada
        try:
            from bcb import Expectativas
            print("✓ Biblioteca python-bcb instalada")
        except ImportError:
            print("✗ Biblioteca python-bcb NÃO instalada")
            print("  Execute: pip install python-bcb")
            return
        
        # Testa conexão
        try:
            em = Expectativas()
            print("✓ API de Expectativas inicializada")
            
            # Lista endpoints disponíveis
            try:
                print("\nTentando listar endpoints disponíveis...")
                # Alguns métodos comuns
                endpoints_teste = [
                    'ExpectativasMercadoInflacao',
                    'ExpectativasMercadoSelic',
                    'ExpectativasMercadoPIB',
                    'ExpectativasMercadoCambio'
                ]
                
                for endpoint_name in endpoints_teste:
                    try:
                        ep = em.get_endpoint(endpoint_name)
                        print(f"  ✓ {endpoint_name} disponível")
                    except Exception as e:
                        print(f"  ✗ {endpoint_name} - Erro: {str(e)}")
                
            except Exception as e:
                print(f"  Erro ao listar endpoints: {str(e)}")
            
            # Testa busca de dados
            print("\nTestando busca de dados...")
            sucesso = buscar_projecoes_focus()
            
            if sucesso:
                print("✓ Busca de dados concluída com sucesso!")
            else:
                print("✗ Busca de dados falhou")
                print("\nTentando método alternativo...")
                sucesso_alt = buscar_dados_focus_manual()
                if sucesso_alt:
                    print("✓ Método alternativo funcionou!")
                else:
                    print("✗ Método alternativo também falhou")
            
            # Verifica dados salvos
            from app.models import FocusData
            latest = FocusData.get_latest()
            if latest:
                print(f"\n✓ Dados mais recentes no banco: {latest.date}")
                print(f"  IPCA 2025: {latest.ipca_2025}")
                print(f"  Selic 2025: {latest.selic_2025}")
            else:
                print("\n✗ Nenhum dado encontrado no banco")
        
        except Exception as e:
            print(f"✗ Erro ao conectar com API: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("TESTE CONCLUÍDO")
        print("=" * 60)

if __name__ == '__main__':
    test_api()




