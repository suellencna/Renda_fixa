from app import db
from flask_login import UserMixin
from datetime import datetime, timedelta

class User(UserMixin, db.Model):
    """Modelo de usuário"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    access_code_id = db.Column(db.Integer, db.ForeignKey('access_codes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_access = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    disclaimer_accepted_at = db.Column(db.DateTime, nullable=True)
    
    access_code = db.relationship('AccessCode', backref='users', lazy=True)
    
    def __repr__(self):
        return f'<User {self.id}>'
    
    def is_access_valid(self):
        """Verifica se o acesso ainda é válido (1 ano)"""
        if not self.access_code:
            return False
        
        if self.access_code.first_used_at is None:
            return True  # Código ainda não foi usado
        
        expiry_date = self.access_code.first_used_at + timedelta(days=365)
        return datetime.utcnow() < expiry_date


class AccessCode(db.Model):
    """Modelo de código de acesso"""
    __tablename__ = 'access_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False)
    first_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=True)  # Admin que criou
    notes = db.Column(db.Text, nullable=True)  # Observações sobre o código
    
    def __repr__(self):
        return f'<AccessCode {self.code}>'
    
    def activate(self):
        """Ativa o código (define primeira data de uso)"""
        if not self.is_used:
            self.is_used = True
            self.first_used_at = datetime.utcnow()
            self.expires_at = datetime.utcnow() + timedelta(days=365)
            db.session.commit()
    
    def is_valid(self):
        """Verifica se o código ainda é válido"""
        if not self.is_used:
            return True  # Código nunca foi usado, ainda é válido
        
        if self.expires_at:
            return datetime.utcnow() < self.expires_at
        
        # Se não tem data de expiração mas foi usado, calcula 1 ano a partir da primeira vez
        if self.first_used_at:
            expiry_date = self.first_used_at + timedelta(days=365)
            return datetime.utcnow() < expiry_date
        
        return False


class FocusData(db.Model):
    """Modelo para armazenar dados do Boletim Focus"""
    __tablename__ = 'focus_data'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    
    # Projeções IPCA (%)
    ipca_2025 = db.Column(db.Float, nullable=True)
    ipca_2026 = db.Column(db.Float, nullable=True)
    ipca_2027 = db.Column(db.Float, nullable=True)
    ipca_2028 = db.Column(db.Float, nullable=True)
    
    # Projeções Selic (% a.a.)
    selic_2025 = db.Column(db.Float, nullable=True)
    selic_2026 = db.Column(db.Float, nullable=True)
    selic_2027 = db.Column(db.Float, nullable=True)
    selic_2028 = db.Column(db.Float, nullable=True)
    
    # Projeções PIB (var. %)
    pib_2025 = db.Column(db.Float, nullable=True)
    pib_2026 = db.Column(db.Float, nullable=True)
    pib_2027 = db.Column(db.Float, nullable=True)
    pib_2028 = db.Column(db.Float, nullable=True)
    
    # Projeções Câmbio (R$/US$)
    cambio_2025 = db.Column(db.Float, nullable=True)
    cambio_2026 = db.Column(db.Float, nullable=True)
    cambio_2027 = db.Column(db.Float, nullable=True)
    cambio_2028 = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FocusData {self.date}>'
    
    @classmethod
    def get_latest(cls):
        """Retorna os dados mais recentes do Focus"""
        return cls.query.order_by(cls.date.desc()).first()


class InvestmentComparison(db.Model):
    """Modelo para armazenar comparações realizadas (opcional, para histórico)"""
    __tablename__ = 'investment_comparisons'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    comparison_type = db.Column(db.String(20), nullable=False)  # '1x1' ou '1xmulti'
    data = db.Column(db.Text, nullable=False)  # JSON com dados da comparação
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='comparisons', lazy=True)
    
    def __repr__(self):
        return f'<InvestmentComparison {self.id}>'

