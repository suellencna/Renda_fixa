"""
Módulo de cálculos financeiros para o comparador de renda fixa
"""
import math
from datetime import datetime
from app.models import FocusData

# Tabelas regressivas de IR
IR_TABLES = {
    '2025': [
        (180, 0.225),   # Até 180 dias: 22,5%
        (360, 0.20),    # 181 a 360 dias: 20%
        (720, 0.175),   # 361 a 720 dias: 17,5%
        (float('inf'), 0.15)  # Acima de 720 dias: 15%
    ],
    '2026': [
        (float('inf'), 0.175)  # Alíquota única de 17,5%
    ]
}

INVESTIMENTOS_ISENTOS_ATE_2025 = {'lci', 'lca', 'debenture_incentivada'}

def get_ir_rate(days, investimento_type=None, tax_regime='2025'):
    """
    Retorna a alíquota de IR baseada no prazo em dias e regime tributário.
    Para 2026, usa alíquotas fixas conforme MP 1.303/2025 (ainda pendente de aprovação).
    """
    tax_regime = tax_regime or '2025'
    
    if tax_regime == '2026':
        if investimento_type in INVESTIMENTOS_ISENTOS_ATE_2025:
            return 0.05  # Alíquota reduzida para ativos antes isentos
        return 0.175
    
    table = IR_TABLES.get('2025')
    for limit, rate in table:
        if days <= limit:
            return rate
    return table[-1][1]

def get_focus_projection(year=None):
    """Retorna projeção do Focus para o ano especificado (ou ano atual)"""
    if year is None:
        year = datetime.now().year
    
    focus = FocusData.get_latest()
    if not focus:
        return None
    
    projections = {}
    if year == 2025:
        projections = {
            'ipca': focus.ipca_2025,
            'selic': focus.selic_2025,
            'pib': focus.pib_2025,
            'cambio': focus.cambio_2025
        }
    elif year == 2026:
        projections = {
            'ipca': focus.ipca_2026,
            'selic': focus.selic_2026,
            'pib': focus.pib_2026,
            'cambio': focus.cambio_2026
        }
    elif year == 2027:
        projections = {
            'ipca': focus.ipca_2027,
            'selic': focus.selic_2027,
            'pib': focus.pib_2027,
            'cambio': focus.cambio_2027
        }
    elif year == 2028:
        projections = {
            'ipca': focus.ipca_2028,
            'selic': focus.selic_2028,
            'pib': focus.pib_2028,
            'cambio': focus.cambio_2028
        }
    
    return projections if any(projections.values()) else None

def calcular_cdi(selic=None):
    """Calcula CDI aproximado (CDI ≈ Selic - 0,10%)"""
    if selic is None:
        # Tenta pegar do Focus
        year = datetime.now().year
        focus = get_focus_projection(year)
        if focus and focus.get('selic'):
            selic = focus['selic'] / 100
        else:
            # Valor padrão se não houver Focus
            selic = 0.15  # 15% a.a.
    else:
        selic = selic / 100
    
    cdi = selic - 0.001  # Selic - 0,10%
    return max(cdi, 0) * 100  # Retorna em porcentagem

def calcular_rentabilidade_bruta(
    investimento_type,
    rentabilidade_type,
    rentabilidade_value,
    valor_inicial,
    aportes_mensais,
    meses,
    selic=None,
    ipca=None,
    taxa_custodia_tesouro=0.002,
    taxa_custos_extra=0.0
):
    """
    Calcula rentabilidade bruta do investimento
    
    Args:
        investimento_type: 'cdb', 'lci', 'lca', 'tesouro_selic', 'tesouro_ipca', 'tesouro_prefixado', 'fundo_di', 'debenture'
        rentabilidade_type: 'prefixado', 'cdi', 'ipca_mais'
        rentabilidade_value: valor da rentabilidade (%, %CDI, ou IPCA+%)
        valor_inicial: valor inicial investido
        aportes_mensais: aportes mensais (0 se não houver)
        meses: prazo em meses
        selic: taxa Selic (opcional, tenta pegar do Focus)
        ipca: taxa IPCA (opcional, tenta pegar do Focus)
    
    Returns:
        dict com valor_bruto, rentabilidade_efetiva, custos
    """
    # Converte meses para anos
    anos = meses / 12
    meses_decimal = meses
    
    # Determina taxa efetiva anual
    if rentabilidade_type == 'prefixado':
        taxa_anual = rentabilidade_value / 100
        
    elif rentabilidade_type == 'cdi':
        cdi_anual = calcular_cdi(selic) / 100
        taxa_anual = (cdi_anual * rentabilidade_value) / 100
        
    elif rentabilidade_type == 'ipca_mais':
        # Tenta pegar IPCA do Focus
        if ipca is None:
            year = datetime.now().year
            focus = get_focus_projection(year)
            if focus and focus.get('ipca'):
                ipca_anual = focus['ipca'] / 100
            else:
                ipca_anual = 0.045  # 4,5% padrão
        else:
            ipca_anual = ipca / 100
        
        taxa_prefixada = rentabilidade_value / 100
        taxa_anual = (1 + ipca_anual) * (1 + taxa_prefixada) - 1
    else:
        taxa_anual = 0
    
    # Taxa mensal
    taxa_mensal = (1 + taxa_anual) ** (1/12) - 1
    
    # Calcula valor bruto com juros compostos
    if aportes_mensais > 0:
        # Fórmula de anuidade (valor futuro com aportes)
        valor_futuro_inicial = valor_inicial * (1 + taxa_mensal) ** meses
        valor_futuro_aportes = aportes_mensais * (((1 + taxa_mensal) ** meses - 1) / taxa_mensal)
        valor_bruto = valor_futuro_inicial + valor_futuro_aportes
    else:
        # Juros compostos simples
        valor_bruto = valor_inicial * (1 + taxa_mensal) ** meses
    
    # Calcula custos (custódia do Tesouro)
    custos = 0
    if investimento_type in ['tesouro_selic', 'tesouro_ipca', 'tesouro_prefixado']:
        custos += valor_bruto * taxa_custodia_tesouro * anos
    
    if taxa_custos_extra > 0:
        custos += valor_bruto * taxa_custos_extra * anos
    
    # Rentabilidade efetiva
    total_investido = valor_inicial + (aportes_mensais * meses)
    rentabilidade_efetiva = ((valor_bruto - total_investido) / total_investido) * 100
    
    return {
        'valor_bruto': valor_bruto,
        'rentabilidade_efetiva': rentabilidade_efetiva,
        'custos': custos,
        'total_investido': total_investido
    }

def calcular_imposto_renda(valor_bruto, total_investido, meses, investimento_type, tax_regime='2025'):
    """
    Calcula imposto de renda sobre o ganho
    
    Args:
        valor_bruto: valor bruto acumulado
        total_investido: total investido (inicial + aportes)
        meses: prazo em meses
        investimento_type: tipo de investimento
    
    Returns:
        valor_ir: valor do imposto a pagar
    """
    tax_regime = tax_regime or '2025'
    
    # Regra vigente até 2025 mantém isenção de LCI/LCA
    if tax_regime == '2025' and investimento_type in INVESTIMENTOS_ISENTOS_ATE_2025:
        return 0
    
    # Calcula ganho
    ganho = valor_bruto - total_investido
    
    if ganho <= 0:
        return 0
    
    # Dias para calcular IR
    dias = meses * 30
    
    # Alíquota de IR
    aliquota = get_ir_rate(dias, investimento_type=investimento_type, tax_regime=tax_regime)
    
    # Valor do IR
    valor_ir = ganho * aliquota
    
    return valor_ir

def ajustar_inflacao(valor_nominal, meses, ipca=None):
    """
    Ajusta valor nominal pela inflação (IPCA)
    
    Args:
        valor_nominal: valor em reais
        meses: prazo em meses
        ipca: taxa IPCA anual (opcional, tenta pegar do Focus)
    
    Returns:
        valor_real: valor ajustado pela inflação
    """
    # Tenta pegar IPCA do Focus
    if ipca is None:
        year = datetime.now().year
        focus = get_focus_projection(year)
        if focus and focus.get('ipca'):
            ipca_anual = focus['ipca'] / 100
        else:
            ipca_anual = 0.045  # 4,5% padrão
    else:
        ipca_anual = ipca / 100
    
    # Taxa mensal de inflação
    ipca_mensal = (1 + ipca_anual) ** (1/12) - 1
    
    # Valor real (descontando inflação)
    valor_real = valor_nominal / ((1 + ipca_mensal) ** meses)
    
    return valor_real

def calcular_investimento_completo(
    investimento_type,
    rentabilidade_type,
    rentabilidade_value,
    valor_inicial,
    aportes_mensais,
    meses,
    incluir_ir=True,
    ajustar_inflacao_flag=True,
    selic=None,
    ipca=None,
    tax_regime='2025',
    taxa_custodia_tesouro=0.002,
    taxa_custos_extra=0.0
):
    """
    Calcula investimento completo com todas as opções
    
    Returns:
        dict com todos os valores calculados
    """
    # Calcula rentabilidade bruta
    resultado = calcular_rentabilidade_bruta(
        investimento_type,
        rentabilidade_type,
        rentabilidade_value,
        valor_inicial,
        aportes_mensais,
        meses,
        selic,
        ipca,
        taxa_custodia_tesouro=taxa_custodia_tesouro,
        taxa_custos_extra=taxa_custos_extra
    )
    
    # Calcula IR
    valor_ir = 0
    if incluir_ir:
        valor_ir = calcular_imposto_renda(
            resultado['valor_bruto'],
            resultado['total_investido'],
            meses,
            investimento_type,
            tax_regime=tax_regime
        )
    
    # Valor líquido (bruto - IR - custos)
    valor_liquido = resultado['valor_bruto'] - valor_ir - resultado['custos']
    
    # Rentabilidade líquida
    ganho_liquido = valor_liquido - resultado['total_investido']
    rentabilidade_liquida = (ganho_liquido / resultado['total_investido']) * 100 if resultado['total_investido'] > 0 else 0
    
    # Ajuste pela inflação
    valor_real = valor_liquido
    ganho_real = ganho_liquido
    if ajustar_inflacao_flag:
        valor_real = ajustar_inflacao(valor_liquido, meses, ipca)
        ganho_real = valor_real - ajustar_inflacao(resultado['total_investido'], meses, ipca)
    
    return {
        'valor_bruto': resultado['valor_bruto'],
        'rentabilidade_bruta': resultado['rentabilidade_efetiva'],
        'custos': resultado['custos'],
        'valor_ir': valor_ir,
        'valor_liquido': valor_liquido,
        'rentabilidade_liquida': rentabilidade_liquida,
        'ganho_liquido': ganho_liquido,
        'valor_real': valor_real,
        'ganho_real': ganho_real,
        'total_investido': resultado['total_investido']
    }


def _calcular_valor_futuro(prefixada_mensal, valor_inicial, aportes_mensais, meses):
    """Calcula valor futuro com taxa mensal e aportes."""
    if prefixada_mensal == 0:
        return valor_inicial + aportes_mensais * meses
    
    valor_futuro_inicial = valor_inicial * (1 + prefixada_mensal) ** meses
    valor_futuro_aportes = 0
    
    if aportes_mensais > 0:
        valor_futuro_aportes = aportes_mensais * (((1 + prefixada_mensal) ** meses - 1) / prefixada_mensal)
    
    return valor_futuro_inicial + valor_futuro_aportes


def simular_investimentos_padrao(
    valor_inicial,
    aportes_mensais,
    meses,
    parametros,
    incluir_ir=True,
    ajustar_inflacao_flag=True,
    tax_regime='2025'
):
    """
    Realiza uma simulação padronizada com múltiplos investimentos de uma vez.
    
    Args:
        valor_inicial (float): aporte inicial.
        aportes_mensais (float): aportes mensais.
        meses (int): prazo da aplicação.
        parametros (dict): dicionário com taxas configuráveis.
    
    Returns:
        list[dict]: lista com resultados formatados por investimento.
    """
    selic = parametros.get('selic', 0.0)
    cdi = parametros.get('cdi', selic)
    ipca = parametros.get('ipca', 0.0)
    taxa_custodia = parametros.get('taxa_custodia', 0.2) / 100
    taxa_admin_fundo_di = parametros.get('taxa_admin_fundo_di', 0.0) / 100
    
    total_investido = valor_inicial + aportes_mensais * meses
    
    resultados = []
    
    def registrar(nome, resultado, investimento_type, rentabilidade_type, rentabilidade_value, taxa_custos_extra=0.0, extras=None):
        extras = extras or {}
        # Calcula evolução mensal
        evolucao_mensal = calcular_evolucao_mensal(
            investimento_type=investimento_type,
            rentabilidade_type=rentabilidade_type,
            rentabilidade_value=rentabilidade_value,
            valor_inicial=valor_inicial,
            aportes_mensais=aportes_mensais,
            meses=meses,
            parametros=parametros,
            incluir_ir=incluir_ir,
            ajustar_inflacao_flag=ajustar_inflacao_flag,
            tax_regime=tax_regime,
            taxa_custos_extra=taxa_custos_extra
        )
        
        resultados.append({
            'nome': nome,
            'total_investido': round(resultado['total_investido'], 2),
            'valor_bruto': round(resultado['valor_bruto'], 2),
            'rentabilidade_bruta': round(resultado['rentabilidade_bruta'], 2),
            'custos': round(resultado['custos'], 2),
            'valor_ir': round(resultado['valor_ir'], 2),
            'valor_liquido': round(resultado['valor_liquido'], 2),
            'rentabilidade_liquida': round(resultado['rentabilidade_liquida'], 2),
            'ganho_liquido': round(resultado['ganho_liquido'], 2),
            'valor_real': round(resultado['valor_real'], 2),
            'ganho_real': round(resultado['ganho_real'], 2),
            'evolucao_mensal': evolucao_mensal,
            **extras
        })
    
    def executar(investimento_type, rentabilidade_type, rentabilidade_value, **kwargs):
        argumentos = {
            'investimento_type': investimento_type,
            'rentabilidade_type': rentabilidade_type,
            'rentabilidade_value': rentabilidade_value,
            'valor_inicial': valor_inicial,
            'aportes_mensais': aportes_mensais,
            'meses': meses,
            'incluir_ir': incluir_ir,
            'ajustar_inflacao_flag': ajustar_inflacao_flag,
            'selic': selic,
            'ipca': ipca,
            'tax_regime': tax_regime,
            'taxa_custodia_tesouro': taxa_custodia
        }
        argumentos.update(kwargs)
        return calcular_investimento_completo(**argumentos)
    
    # LCI/LCA (isentos até 2025)
    rent_lci = parametros.get('rentabilidade_lci_lca', 90.0)
    resultado_lci = executar(
        investimento_type='lci',
        rentabilidade_type='cdi',
        rentabilidade_value=rent_lci,
        taxa_custos_extra=0.0
    )
    registrar('LCI e LCA', resultado_lci, 'lci', 'cdi', rent_lci, 0.0)
    
    # CDB
    rent_cdb = parametros.get('rentabilidade_cdb', 100.0)
    resultado_cdb = executar(
        investimento_type='cdb',
        rentabilidade_type='cdi',
        rentabilidade_value=rent_cdb,
        taxa_custos_extra=0.0
    )
    registrar('CDB', resultado_cdb, 'cdb', 'cdi', rent_cdb, 0.0)
    
    # Tesouro Selic
    selic_val = parametros.get('selic', selic)
    resultado_selic = executar(
        investimento_type='tesouro_selic',
        rentabilidade_type='prefixado',
        rentabilidade_value=selic_val,
        taxa_custos_extra=0.0
    )
    registrar('Tesouro Selic', resultado_selic, 'tesouro_selic', 'prefixado', selic_val, 0.0)
    
    # Fundo DI
    rent_fundo = parametros.get('rentabilidade_fundo_di', 95.0)
    resultado_fundo_di = executar(
        investimento_type='fundo_di',
        rentabilidade_type='cdi',
        rentabilidade_value=rent_fundo,
        taxa_custos_extra=taxa_admin_fundo_di
    )
    registrar('Fundo DI', resultado_fundo_di, 'fundo_di', 'cdi', rent_fundo, taxa_admin_fundo_di)
    
    # Tesouro Prefixado
    tesouro_pref = parametros.get('tesouro_prefixado_nominal', selic)
    resultado_prefixado = executar(
        investimento_type='tesouro_prefixado',
        rentabilidade_type='prefixado',
        rentabilidade_value=tesouro_pref,
        taxa_custos_extra=0.0
    )
    registrar('Tesouro Prefixado', resultado_prefixado, 'tesouro_prefixado', 'prefixado', tesouro_pref, 0.0)
    
    # Tesouro IPCA+
    tesouro_ipca_val = parametros.get('tesouro_ipca_mais', 5.0)
    resultado_ipca = executar(
        investimento_type='tesouro_ipca',
        rentabilidade_type='ipca_mais',
        rentabilidade_value=tesouro_ipca_val,
        taxa_custos_extra=0.0
    )
    registrar('Tesouro IPCA+', resultado_ipca, 'tesouro_ipca', 'ipca_mais', tesouro_ipca_val, 0.0)
    
    # Poupança
    poupanca_mensal = parametros.get('poupanca_mensal', 0.5) / 100
    poupanca_anual = ((1 + poupanca_mensal) ** 12 - 1) * 100
    resultado_poupanca = executar(
        investimento_type='poupanca',
        rentabilidade_type='prefixado',
        rentabilidade_value=poupanca_anual,
        incluir_ir=False,
        taxa_custos_extra=0.0
    )
    registrar('Poupança', resultado_poupanca, 'poupanca', 'prefixado', poupanca_anual, 0.0)
    
    # Correção pelo IPCA (apenas atualização pela inflação)
    ipca_anual = ipca / 100 if ipca else 0.0
    ipca_mensal = (1 + ipca_anual) ** (1/12) - 1 if ipca_anual else 0.0
    valor_corrigido = _calcular_valor_futuro(ipca_mensal, valor_inicial, aportes_mensais, meses)
    ganho_corrigido = valor_corrigido - total_investido
    
    # Calcula evolução mensal para IPCA
    evolucao_ipca = []
    valor_atual_ipca = valor_inicial
    for mes in range(1, meses + 1):
        if aportes_mensais > 0:
            valor_atual_ipca = valor_atual_ipca * (1 + ipca_mensal) + aportes_mensais
        else:
            valor_atual_ipca = valor_atual_ipca * (1 + ipca_mensal)
        evolucao_ipca.append({
            'mes': mes,
            'valor_liquido': round(valor_atual_ipca, 2)
        })
    
    resultados.append({
        'nome': 'Correção pelo IPCA',
        'total_investido': round(total_investido, 2),
        'valor_bruto': round(valor_corrigido, 2),
        'rentabilidade_bruta': round((ganho_corrigido / total_investido) * 100 if total_investido else 0, 2),
        'custos': 0.0,
        'valor_ir': 0.0,
        'valor_liquido': round(valor_corrigido, 2),
        'rentabilidade_liquida': round((ganho_corrigido / total_investido) * 100 if total_investido else 0, 2),
        'ganho_liquido': round(ganho_corrigido, 2),
        'valor_real': round(valor_corrigido, 2),
        'ganho_real': round(ganho_corrigido, 2),
        'evolucao_mensal': evolucao_ipca
    })
    
    return resultados


def calcular_evolucao_mensal(
    investimento_type,
    rentabilidade_type,
    rentabilidade_value,
    valor_inicial,
    aportes_mensais,
    meses,
    parametros,
    incluir_ir=True,
    ajustar_inflacao_flag=True,
    tax_regime='2025',
    taxa_custos_extra=0.0
):
    """
    Calcula a evolução mensal do valor líquido de um investimento.
    
    Returns:
        list[dict]: lista com {'mes': int, 'valor_liquido': float} para cada mês
    """
    selic = parametros.get('selic', 0.0)
    cdi = parametros.get('cdi', selic)
    ipca = parametros.get('ipca', 0.0)
    taxa_custodia = parametros.get('taxa_custodia', 0.2) / 100
    
    # Determina taxa efetiva anual
    if rentabilidade_type == 'prefixado':
        taxa_anual = rentabilidade_value / 100
    elif rentabilidade_type == 'cdi':
        cdi_anual = cdi / 100
        taxa_anual = (cdi_anual * rentabilidade_value) / 100
    elif rentabilidade_type == 'ipca_mais':
        ipca_anual = ipca / 100
        taxa_prefixada = rentabilidade_value / 100
        taxa_anual = (1 + ipca_anual) * (1 + taxa_prefixada) - 1
    else:
        taxa_anual = 0
    
    # Aplica taxa de administração (Fundo DI)
    if taxa_custos_extra > 0:
        taxa_anual = taxa_anual - taxa_custos_extra
    
    # Taxa mensal
    taxa_mensal = (1 + taxa_anual) ** (1/12) - 1
    
    evolucao = []
    valor_atual = valor_inicial
    
    for mes in range(1, meses + 1):
        # Calcula valor bruto no mês
        if aportes_mensais > 0:
            valor_atual = valor_atual * (1 + taxa_mensal) + aportes_mensais
        else:
            valor_atual = valor_atual * (1 + taxa_mensal)
        
        # Calcula custos acumulados até o mês
        custos = 0
        if investimento_type in ['tesouro_selic', 'tesouro_ipca', 'tesouro_prefixado']:
            anos_decorridos = mes / 12
            custos = valor_atual * taxa_custodia * anos_decorridos
        
        # Calcula IR acumulado até o mês
        total_investido_mes = valor_inicial + (aportes_mensais * mes)
        ganho_bruto = valor_atual - total_investido_mes
        
        valor_ir = 0
        if incluir_ir and ganho_bruto > 0:
            dias = mes * 30
            aliquota = get_ir_rate(dias, investimento_type=investimento_type, tax_regime=tax_regime)
            
            # Verifica isenção
            if not (tax_regime == '2025' and investimento_type in INVESTIMENTOS_ISENTOS_ATE_2025):
                valor_ir = ganho_bruto * aliquota
        
        # Valor líquido
        valor_liquido = valor_atual - valor_ir - custos
        
        evolucao.append({
            'mes': mes,
            'valor_liquido': round(valor_liquido, 2)
        })
    
    return evolucao


