from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.models import AccessCode, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de login com código de acesso"""
    if request.method == 'POST':
        fixed_code = current_app.config.get('ACCESS_CODE_DEFAULT', '').strip().upper()
        code = request.form.get('code', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        
        if not code:
            flash('Por favor, digite seu código de acesso.', 'error')
            return render_template('login.html')
        
        if fixed_code and code != fixed_code:
            flash('Código de acesso inválido. Verifique se digitou corretamente.', 'error')
            return render_template('login.html')
        
        if not email:
            flash('Informe um e-mail válido para continuar.', 'error')
            return render_template('login.html')
        
        # Garante existência do código fixo
        access_code = AccessCode.query.filter_by(code=fixed_code).first()
        if not access_code:
            access_code = AccessCode(code=fixed_code, created_by='system')
            db.session.add(access_code)
            db.session.commit()
        
        if not access_code.is_used:
            access_code.activate()
        
        # Busca usuário pelo e-mail
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                email=email,
                name=name or None,
                access_code_id=access_code.id
            )
            db.session.add(user)
        else:
            if name and not user.name:
                user.name = name
            if user.access_code_id != access_code.id:
                user.access_code_id = access_code.id
        
        user.last_access = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=True)
        session['accepted_disclaimer'] = bool(user.disclaimer_accepted_at)
        
        flash('Login realizado com sucesso!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    logout_user()
    session.pop('accepted_disclaimer', None)
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('auth.login'))

