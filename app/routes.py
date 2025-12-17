import json
import os
from pathlib import Path

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, url_for, current_app, session, redirect, Response
from flask_login import login_required, current_user
from app import db
from app.models import FocusData
from app.calculations import (
    calcular_investimento_completo,
    get_focus_projection,
    simular_investimentos_padrao
)

main_bp = Blueprint('main', __name__)

_DISCLAIMER_ALLOWED_ENDPOINTS = {
    'main.disclaimer',
    'main.accept_disclaimer',
    'auth.logout',
    'auth.login'
}

@main_bp.before_app_request
def _require_disclaimer_acceptance():
    if not current_user.is_authenticated:
        return
    if getattr(current_user, 'disclaimer_accepted_at', None):
        session['accepted_disclaimer'] = True
        return
    endpoint = request.endpoint or ''
    if endpoint.startswith('static'):
        return
    if endpoint in _DISCLAIMER_ALLOWED_ENDPOINTS:
        return
    return redirect(url_for('main.disclaimer'))

def _get_latest_focus_pdf():
    """Retorna a URL do PDF mais recente do Boletim Focus armazenado em static/focus"""
    focus_dir = os.path.join(current_app.static_folder, 'focus')
    
    if not os.path.isdir(focus_dir):
        return None
    
    pdf_files = [
        f for f in os.listdir(focus_dir)
        if os.path.isfile(os.path.join(focus_dir, f)) and f.lower().endswith('.pdf')
    ]
    
    if not pdf_files:
        return None
    
    latest_pdf = max(
        pdf_files,
        key=lambda f: os.path.getmtime(os.path.join(focus_dir, f))
    )
    
    return url_for('static', filename=f'focus/{latest_pdf}')

def _load_latest_rates():
    """Carrega o arquivo JSON com as taxas mais recentes, se existir."""
    base_path = Path(current_app.root_path).parent
    rates_path = base_path / "data" / "taxas.json"
    
    if not rates_path.exists():
        return {}
    
    try:
        with rates_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}

def _rate_value(rates, key, default, ndigits=2):
    value = rates.get(key)
    if value is None:
        return default
    try:
        return round(float(value), ndigits)
    except Exception:
        return default

@main_bp.route('/')
@login_required
def index():
    """Página inicial - Comparação 1x1"""
    focus_data = FocusData.get_latest()
    return render_template('index.html', focus_data=focus_data)

@main_bp.route('/compare-multi')
@login_required
def compare_multi():
    """Página de comparação 1x vários"""
    focus_data = FocusData.get_latest()
    return render_template('compare_multi.html', focus_data=focus_data)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Painel com projeções do Focus"""
    focus_data = FocusData.get_latest()
    focus_pdf = _get_latest_focus_pdf()
    return render_template('dashboard.html', focus_data=focus_data, focus_pdf=focus_pdf)

@main_bp.route('/simulador-renda-fixa')
@login_required
def simulador_renda_fixa():
    """Página da calculadora rápida de renda fixa."""
    focus_data = FocusData.get_latest()
    rates = _load_latest_rates()

    selic = _rate_value(rates, 'selic_meta', 10.0)
    cdi = _rate_value(rates, 'cdi_over', selic)
    ipca = _rate_value(rates, 'ipca_12m', 4.0)
    tr = _rate_value(rates, 'tr_mensal', 0.17, ndigits=4)
    poupanca_mensal = _rate_value(rates, 'poupanca_mensal', 0.6731, ndigits=4)

    # Percentuais relativos ao CDI
    rentabilidade_cdb = 100.0
    rentabilidade_fundo_di = 98.0
    rentabilidade_lci_lca = 85.0

    if rates.get('fundo_di_liquido') and rates.get('cdi_over'):
        rentabilidade_fundo_di = round(
            (float(rates['fundo_di_liquido']) / float(rates['cdi_over'])) * 100,
            2
        )
    if rates.get('lci_lca_85_cdi') and rates.get('cdi_over'):
        rentabilidade_lci_lca = round(
            (float(rates['lci_lca_85_cdi']) / float(rates['cdi_over'])) * 100,
            2
        )
    
    tesouro_prefixado = rates.get('tesouro_prefixado_nominal')
    if tesouro_prefixado is None and focus_data and focus_data.selic_2025:
        tesouro_prefixado = round(focus_data.selic_2025, 2)
    tesouro_prefixado = _rate_value(
        {'tmp': tesouro_prefixado} if tesouro_prefixado is not None else {},
        'tmp',
        10.0
    )

    tesouro_ipca = _rate_value(rates, 'tesouro_ipca_mais', 6.5)
    taxa_admin_fundo_di = _rate_value(rates, 'taxa_admin_fundo_di', 0.25)
    
    default_params = {
        'selic': selic,
        'cdi': cdi,
        'ipca': ipca,
        'tr': tr,
        'taxa_custodia': 0.20,
        'tesouro_prefixado_nominal': tesouro_prefixado,
        'tesouro_ipca_mais': tesouro_ipca,
        'taxa_admin_fundo_di': taxa_admin_fundo_di,
        'rentabilidade_cdb': rentabilidade_cdb,
        'rentabilidade_fundo_di': rentabilidade_fundo_di,
        'rentabilidade_lci_lca': rentabilidade_lci_lca,
        'poupanca_mensal': poupanca_mensal
    }
    
    return render_template(
        'simulador_renda_fixa.html',
        focus_data=focus_data,
        default_params=default_params
    )

@main_bp.route('/disclaimer')
def disclaimer():
    """Página de exoneração de responsabilidade"""
    focus_data = FocusData.get_latest()
    require_acceptance = current_user.is_authenticated and not getattr(current_user, 'disclaimer_accepted_at', None)
    return render_template('disclaimer.html', focus_data=focus_data, require_acceptance=require_acceptance)

@main_bp.route('/disclaimer/aceitar', methods=['POST'])
@login_required
def accept_disclaimer():
    current_user.disclaimer_accepted_at = datetime.utcnow()
    db.session.commit()
    session['accepted_disclaimer'] = True
    flash('Obrigado! Os termos foram aceitos.', 'success')
    next_page = request.args.get('next')
    return redirect(next_page or url_for('main.index'))

def _is_admin_user():
    if not current_user.is_authenticated:
        return False
    admins = current_app.config.get('ADMIN_EMAILS') or []
    admins = [adm.strip().lower() for adm in admins if adm.strip()]
    if not admins:
        return False
    return (current_user.email or '').lower() in admins

@main_bp.app_context_processor
def inject_admin_flag():
    return {'is_admin_user': _is_admin_user()}

@main_bp.route('/admin/usuarios')
@login_required
def admin_users():
    if not _is_admin_user():
        flash('Acesso restrito.', 'error')
        return redirect(url_for('main.index'))
    from app.models import User
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@main_bp.route('/admin/usuarios/<int:user_id>/reset', methods=['POST'])
@login_required
def admin_reset_user_disclaimer(user_id):
    if not _is_admin_user():
        flash('Acesso restrito.', 'error')
        return redirect(url_for('main.index'))
    from app.models import User
    user = User.query.get_or_404(user_id)
    user.disclaimer_accepted_at = None
    db.session.commit()
    flash(f'Aceite de {user.email or "usuário"} foi resetado.', 'info')
    return redirect(url_for('main.admin_users'))

@main_bp.route('/admin/usuarios/export')
@login_required
def admin_export_users():
    if not _is_admin_user():
        flash('Acesso restrito.', 'error')
        return redirect(url_for('main.index'))
    from app.models import User
    users = User.query.order_by(User.created_at.desc()).all()
    lines = ['nome,email,criado_em,ultimo_acesso,aceite_disclaimer']
    for u in users:
        lines.append(f'"{u.name or ""}","{u.email or ""}",{u.created_at},{u.last_access},{u.disclaimer_accepted_at}')
    csv_data = '\n'.join(lines)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=usuarios.csv'}
    )

@main_bp.route('/api/calculate', methods=['POST'])
@login_required
def api_calculate():
    """API para calcular investimento"""
    try:
        data = request.get_json()
        
        # Validação dos dados
        required_fields = ['investimento_type', 'rentabilidade_type', 'rentabilidade_value',
                          'valor_inicial', 'aportes_mensais', 'meses']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório faltando: {field}'}), 400
        
        # Parâmetros
        investimento_type = data['investimento_type']
        rentabilidade_type = data['rentabilidade_type']
        rentabilidade_value = float(data['rentabilidade_value'])
        valor_inicial = float(data['valor_inicial'])
        aportes_mensais = float(data.get('aportes_mensais', 0))
        meses = int(data['meses'])
        incluir_ir = data.get('incluir_ir', True)
        ajustar_inflacao = data.get('ajustar_inflacao', True)
        tax_regime = data.get('tax_regime', '2025')
        
        if tax_regime not in ['2025', '2026']:
            return jsonify({'error': 'Regime tributário inválido. Use "2025" ou "2026".'}), 400
        
        # Validações básicas
        if valor_inicial <= 0:
            return jsonify({'error': 'Valor inicial deve ser maior que zero'}), 400
        if meses <= 0:
            return jsonify({'error': 'Prazo deve ser maior que zero'}), 400
        if rentabilidade_value < 0:
            return jsonify({'error': 'Rentabilidade não pode ser negativa'}), 400
        
        # Calcula investimento
        resultado = calcular_investimento_completo(
            investimento_type=investimento_type,
            rentabilidade_type=rentabilidade_type,
            rentabilidade_value=rentabilidade_value,
            valor_inicial=valor_inicial,
            aportes_mensais=aportes_mensais,
            meses=meses,
            incluir_ir=incluir_ir,
            ajustar_inflacao_flag=ajustar_inflacao,
            tax_regime=tax_regime
        )
        
        # Formata valores para exibição
        resultado_formatado = {
            'total_investido': round(resultado['total_investido'], 2),
            'valor_bruto': round(resultado['valor_bruto'], 2),
            'rentabilidade_bruta': round(resultado['rentabilidade_bruta'], 2),
            'custos': round(resultado['custos'], 2),
            'valor_ir': round(resultado['valor_ir'], 2),
            'valor_liquido': round(resultado['valor_liquido'], 2),
            'rentabilidade_liquida': round(resultado['rentabilidade_liquida'], 2),
            'ganho_liquido': round(resultado['ganho_liquido'], 2),
            'valor_real': round(resultado['valor_real'], 2),
            'ganho_real': round(resultado['ganho_real'], 2)
        }
        
        return jsonify(resultado_formatado)
    
    except Exception as e:
        return jsonify({'error': f'Erro ao calcular: {str(e)}'}), 500

@main_bp.route('/api/focus', methods=['GET'])
@login_required
def api_focus():
    """API para retornar dados do Focus"""
    focus_data = FocusData.get_latest()
    
    if not focus_data:
        return jsonify({'error': 'Dados do Focus não disponíveis'}), 404
    
    return jsonify({
        'date': focus_data.date.isoformat(),
        'ipca': {
            '2025': focus_data.ipca_2025,
            '2026': focus_data.ipca_2026,
            '2027': focus_data.ipca_2027,
            '2028': focus_data.ipca_2028
        },
        'selic': {
            '2025': focus_data.selic_2025,
            '2026': focus_data.selic_2026,
            '2027': focus_data.selic_2027,
            '2028': focus_data.selic_2028
        },
        'pib': {
            '2025': focus_data.pib_2025,
            '2026': focus_data.pib_2026,
            '2027': focus_data.pib_2027,
            '2028': focus_data.pib_2028
        },
        'cambio': {
            '2025': focus_data.cambio_2025,
            '2026': focus_data.cambio_2026,
            '2027': focus_data.cambio_2027,
            '2028': focus_data.cambio_2028
        }
    })

@main_bp.route('/api/simular-renda-fixa', methods=['POST'])
@login_required
def api_simular_renda_fixa():
    """API para simular múltiplas aplicações de renda fixa de uma vez."""
    try:
        data = request.get_json()
        
        required_fields = ['valor_inicial', 'meses', 'parametros']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório faltando: {field}'}), 400
        
        valor_inicial = float(data['valor_inicial'])
        aportes_mensais = float(data.get('aportes_mensais', 0.0))
        meses = int(data['meses'])
        parametros = data.get('parametros', {})
        incluir_ir = data.get('incluir_ir', True)
        ajustar_inflacao = data.get('ajustar_inflacao', True)
        tax_regime = data.get('tax_regime', '2025')
        
        if valor_inicial <= 0:
            return jsonify({'error': 'Valor inicial deve ser maior que zero'}), 400
        if meses <= 0:
            return jsonify({'error': 'Prazo deve ser maior que zero'}), 400
        if tax_regime not in ['2025', '2026']:
            return jsonify({'error': 'Regime tributário inválido. Use "2025" ou "2026".'}), 400
        
        resultados = simular_investimentos_padrao(
            valor_inicial=valor_inicial,
            aportes_mensais=aportes_mensais,
            meses=meses,
            parametros=parametros,
            incluir_ir=incluir_ir,
            ajustar_inflacao_flag=ajustar_inflacao,
            tax_regime=tax_regime
        )
        
        return jsonify({'resultados': resultados})
    
    except Exception as exc:
        return jsonify({'error': f'Erro ao calcular: {str(exc)}'}), 500

