"""
Módulo administrativo para gerenciar códigos de acesso
Pode ser expandido no futuro para incluir outras funcionalidades administrativas
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AccessCode, User
from app.utils import gerar_codigo_acesso
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/codes')
@login_required
def list_codes():
    """Lista todos os códigos de acesso"""
    # TODO: Adicionar verificação de permissão de admin
    codes = AccessCode.query.order_by(AccessCode.created_at.desc()).all()
    return render_template('admin/codes.html', codes=codes)

@admin_bp.route('/codes/create', methods=['POST'])
@login_required
def create_code():
    """Cria um novo código de acesso"""
    # TODO: Adicionar verificação de permissão de admin
    
    try:
        prefixo = request.form.get('prefixo', 'POTENS')
        quantidade = int(request.form.get('quantidade', 1))
        
        codigos_criados = []
        
        for _ in range(quantidade):
            codigo = gerar_codigo_acesso(prefixo)
            
            # Verifica se já existe
            while AccessCode.query.filter_by(code=codigo).first():
                codigo = gerar_codigo_acesso(prefixo)
            
            access_code = AccessCode(
                code=codigo,
                created_by=current_user.id if current_user.is_authenticated else 'Admin'
            )
            
            db.session.add(access_code)
            codigos_criados.append(codigo)
        
        db.session.commit()
        
        flash(f'{quantidade} código(s) criado(s) com sucesso!', 'success')
        return redirect(url_for('admin.list_codes'))
    
    except Exception as e:
        flash(f'Erro ao criar código: {str(e)}', 'error')
        return redirect(url_for('admin.list_codes'))

@admin_bp.route('/codes/<int:code_id>/delete', methods=['POST'])
@login_required
def delete_code(code_id):
    """Remove um código de acesso"""
    # TODO: Adicionar verificação de permissão de admin
    
    code = AccessCode.query.get_or_404(code_id)
    
    # Verifica se o código foi usado
    if code.is_used:
        flash('Não é possível remover um código que já foi usado.', 'error')
        return redirect(url_for('admin.list_codes'))
    
    db.session.delete(code)
    db.session.commit()
    
    flash('Código removido com sucesso!', 'success')
    return redirect(url_for('admin.list_codes'))

@admin_bp.route('/codes/<int:code_id>/status')
@login_required
def code_status(code_id):
    """Retorna o status de um código de acesso"""
    code = AccessCode.query.get_or_404(code_id)
    
    return jsonify({
        'code': code.code,
        'is_used': code.is_used,
        'is_valid': code.is_valid(),
        'first_used_at': code.first_used_at.isoformat() if code.first_used_at else None,
        'expires_at': code.expires_at.isoformat() if code.expires_at else None,
        'users_count': len(code.users) if code.users else 0
    })






