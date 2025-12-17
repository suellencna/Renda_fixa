"""
Módulo para capturar dados do Boletim Focus do BCB usando a API oficial
Biblioteca: python-bcb
Documentação: https://wilsonfreitas.github.io/python-bcb/
API: https://dadosabertos.bcb.gov.br/dataset/expectativas-mercado
"""
from datetime import date, datetime
from app import db
from app.models import FocusData
import pandas as pd

def buscar_projecoes_focus():
    """
    Busca projeções do Boletim Focus usando a API oficial do BCB
    Retorna True se conseguiu atualizar, False caso contrário
    """
    try:
        from bcb import Expectativas
        
        # Verifica se já existe dados para hoje
        hoje = date.today()
        focus_existente = FocusData.query.filter_by(date=hoje).first()
        
        if focus_existente:
            # Já atualizado hoje
            print(f"Dados do Focus já atualizados para {hoje}")
            return True
        
        # Instancia a API de expectativas
        em = Expectativas()
        
        # Busca dados das medianas (expectativas de mercado)
        # Usa ExpectativasMercadoAnuais que contém todos os indicadores
        dados = buscar_dados_anuais(em)
        
        # Cria ou atualiza registro
        novo_focus = FocusData(
            date=hoje,
            ipca_2025=dados.get('ipca', {}).get(2025),
            ipca_2026=dados.get('ipca', {}).get(2026),
            ipca_2027=dados.get('ipca', {}).get(2027),
            ipca_2028=dados.get('ipca', {}).get(2028),
            selic_2025=dados.get('selic', {}).get(2025),
            selic_2026=dados.get('selic', {}).get(2026),
            selic_2027=dados.get('selic', {}).get(2027),
            selic_2028=dados.get('selic', {}).get(2028),
            pib_2025=dados.get('pib', {}).get(2025),
            pib_2026=dados.get('pib', {}).get(2026),
            pib_2027=dados.get('pib', {}).get(2027),
            pib_2028=dados.get('pib', {}).get(2028),
            cambio_2025=dados.get('cambio', {}).get(2025),
            cambio_2026=dados.get('cambio', {}).get(2026),
            cambio_2027=dados.get('cambio', {}).get(2027),
            cambio_2028=dados.get('cambio', {}).get(2028)
        )
        
        db.session.add(novo_focus)
        db.session.commit()
        
        print(f"Dados do Focus atualizados com sucesso para {hoje}")
        return True
    
    except ImportError:
        print("Erro: Biblioteca python-bcb não instalada. Execute: pip install python-bcb")
        return False
    except Exception as e:
        print(f"Erro ao buscar dados do Focus: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def buscar_dados_anuais(expectativas_api):
    """
    Busca dados anuais de todos os indicadores usando ExpectativasMercadoAnuais
    
    Args:
        expectativas_api: Instância da API Expectativas
    
    Returns:
        dict com dados por indicador e ano: {'ipca': {2025: valor, ...}, 'selic': {...}, ...}
    """
    dados = {}
    
    try:
        # Obtém o endpoint de expectativas anuais
        ep = expectativas_api.get_endpoint('ExpectativasMercadoAnuais')
        
        # Query para buscar dados
        query = ep.query()
        
        # Coleta todos os dados
        df = query.collect()
        
        if df is not None and not df.empty:
            # Converte para DataFrame se necessário
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)
            
            print(f"Colunas disponíveis: {list(df.columns)}")
            
            # Processa dados por indicador
            # Mapeia indicadores
            indicadores = {
                'IPCA': 'ipca',
                'Selic': 'selic',
                'PIB Total': 'pib',
                'PIB': 'pib',
                'Câmbio': 'cambio',
                'Câmbio R$/US$': 'cambio'
            }
            
            # Ano atual
            ano_atual = datetime.now().year
            anos = [ano_atual, ano_atual + 1, ano_atual + 2, ano_atual + 3]
            
            # Verifica colunas disponíveis
            if 'Indicador' not in df.columns:
                print("Coluna 'Indicador' não encontrada")
                return dados
            
            # Coluna de data (pode ser DataReferencia, Data, ou outra)
            coluna_data = None
            for col in ['DataReferencia', 'Data', 'dataReferencia', 'data']:
                if col in df.columns:
                    coluna_data = col
                    break
            
            if not coluna_data:
                print("Coluna de data não encontrada")
                return dados
            
            # Coluna de valor (pode ser Mediana, Media, ou outra)
            coluna_valor = None
            for col in ['Mediana', 'Media', 'mediana', 'media']:
                if col in df.columns:
                    coluna_valor = col
                    break
            
            if not coluna_valor:
                print("Coluna de valor não encontrada")
                return dados
            
            # Converte data para datetime
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
            
            # Inicializa estrutura de dados
            for indicador_nome, indicador_key in indicadores.items():
                if indicador_key not in dados:
                    dados[indicador_key] = {}
            
            # Processa cada indicador
            for indicador_nome, indicador_key in indicadores.items():
                # Filtra dados do indicador
                df_ind = df[df['Indicador'].str.contains(indicador_nome, case=False, na=False)]
                
                if df_ind.empty:
                    continue
                
                # Processa por ano
                for ano in anos:
                    # Filtra dados do ano
                    df_ano = df_ind[df_ind[coluna_data].dt.year == ano]
                    
                    if not df_ano.empty:
                        # Pega a última mediana disponível
                        valor = df_ano[coluna_valor].iloc[-1]
                        if pd.notna(valor):
                            dados[indicador_key][ano] = float(valor)
            
            # Se não encontrou dados, tenta buscar Selic separadamente
            if not dados.get('selic'):
                dados_selic = buscar_selic_separado(expectativas_api)
                if dados_selic:
                    dados['selic'] = dados_selic
            
            # Se não encontrou IPCA, tenta buscar separadamente
            if not dados.get('ipca'):
                dados_ipca = buscar_inflacao_separado(expectativas_api)
                if dados_ipca:
                    dados['ipca'] = dados_ipca
        
        return dados
    
    except Exception as e:
        print(f"Erro ao buscar dados anuais: {str(e)}")
        import traceback
        traceback.print_exc()
        return dados

def buscar_selic_separado(expectativas_api):
    """Busca dados de Selic usando endpoint específico"""
    try:
        ep = expectativas_api.get_endpoint('ExpectativasMercadoSelic')
        query = ep.query()
        df = query.collect()
        
        if df is not None and not df.empty:
            df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df
            
            # Verifica colunas
            coluna_data = None
            for col in ['DataReferencia', 'Data', 'dataReferencia', 'data']:
                if col in df.columns:
                    coluna_data = col
                    break
            
            if not coluna_data:
                return {}
            
            coluna_valor = None
            for col in ['Mediana', 'Media', 'mediana', 'media']:
                if col in df.columns:
                    coluna_valor = col
                    break
            
            if not coluna_valor:
                return {}
            
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
            
            dados = {}
            ano_atual = datetime.now().year
            anos = [ano_atual, ano_atual + 1, ano_atual + 2, ano_atual + 3]
            
            for ano in anos:
                df_ano = df[df[coluna_data].dt.year == ano]
                if not df_ano.empty:
                    valor = df_ano[coluna_valor].iloc[-1]
                    if pd.notna(valor):
                        dados[ano] = float(valor)
            
            return dados
    except Exception as e:
        print(f"Erro ao buscar Selic: {str(e)}")
        return {}

def buscar_inflacao_separado(expectativas_api):
    """Busca dados de inflação (IPCA) usando endpoint específico"""
    try:
        # Tenta endpoint de inflação 12 meses
        ep = expectativas_api.get_endpoint('ExpectativasMercadoInflacao12Meses')
        query = ep.query()
        df = query.collect()
        
        if df is not None and not df.empty:
            df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df
            
            # Verifica colunas
            coluna_data = None
            for col in ['DataReferencia', 'Data', 'dataReferencia', 'data']:
                if col in df.columns:
                    coluna_data = col
                    break
            
            if not coluna_data:
                return {}
            
            coluna_valor = None
            for col in ['Mediana', 'Media', 'mediana', 'media']:
                if col in df.columns:
                    coluna_valor = col
                    break
            
            if not coluna_valor:
                return {}
            
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
            
            dados = {}
            ano_atual = datetime.now().year
            anos = [ano_atual, ano_atual + 1, ano_atual + 2, ano_atual + 3]
            
            # Para inflação, pode ser necessário processar por período
            # Por enquanto, usa o último valor disponível para cada ano
            for ano in anos:
                df_ano = df[df[coluna_data].dt.year == ano]
                if not df_ano.empty:
                    valor = df_ano[coluna_valor].iloc[-1]
                    if pd.notna(valor):
                        dados[ano] = float(valor)
            
            return dados
    except Exception as e:
        print(f"Erro ao buscar inflação: {str(e)}")
        return {}

def buscar_dados_focus_manual():
    """
    Função alternativa para buscar dados do Focus manualmente
    Usa método mais direto da API
    """
    try:
        from bcb import Expectativas
        
        em = Expectativas()
        hoje = date.today()
        
        # Verifica se já existe
        focus_existente = FocusData.query.filter_by(date=hoje).first()
        if focus_existente:
            return True
        
        # Busca dados usando método principal
        dados = buscar_dados_anuais(em)
        
        # Se não encontrou, tenta buscar Selic separadamente
        if not dados.get('selic'):
            dados['selic'] = buscar_selic_separado(em)
        
        # Se não encontrou IPCA, tenta buscar separadamente
        if not dados.get('ipca'):
            dados['ipca'] = buscar_inflacao_separado(em)
        
        # Cria registro no banco
        if dados:
            novo_focus = FocusData(
                date=hoje,
                ipca_2025=dados.get('ipca', {}).get(2025),
                ipca_2026=dados.get('ipca', {}).get(2026),
                ipca_2027=dados.get('ipca', {}).get(2027),
                ipca_2028=dados.get('ipca', {}).get(2028),
                selic_2025=dados.get('selic', {}).get(2025),
                selic_2026=dados.get('selic', {}).get(2026),
                selic_2027=dados.get('selic', {}).get(2027),
                selic_2028=dados.get('selic', {}).get(2028),
                pib_2025=dados.get('pib', {}).get(2025),
                pib_2026=dados.get('pib', {}).get(2026),
                pib_2027=dados.get('pib', {}).get(2027),
                pib_2028=dados.get('pib', {}).get(2028),
                cambio_2025=dados.get('cambio', {}).get(2025),
                cambio_2026=dados.get('cambio', {}).get(2026),
                cambio_2027=dados.get('cambio', {}).get(2027),
                cambio_2028=dados.get('cambio', {}).get(2028)
            )
            
            db.session.add(novo_focus)
            db.session.commit()
            return True
        
        return False
    
    except Exception as e:
        print(f"Erro no método manual: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
