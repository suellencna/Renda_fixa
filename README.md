# Comparador de Renda Fixa

Sistema web para comparar investimentos de renda fixa de forma simples e intuitiva.

## Funcionalidades

- **Comparação 1x1**: Compare dois investimentos lado a lado
- **Comparação 1x Vários**: Compare um investimento principal com múltiplos investimentos
- **Integração com Boletim Focus**: Dados atualizados do Banco Central do Brasil
- **Cálculos precisos**: Inclui impostos (IR regressivo) e ajuste pela inflação (IPCA)
- **Linguagem simples**: Interface pensada para leigos em investimentos
- **Sistema de acesso**: Controle de acesso por códigos únicos com validade de 1 ano

## Tipos de Investimentos Suportados

- CDB (Certificado de Depósito Bancário)
- LCI (Letra de Crédito Imobiliário)
- LCA (Letra de Crédito do Agronegócio)
- Tesouro Selic
- Tesouro IPCA+
- Tesouro Prefixado
- Fundo DI
- Debêntures

## Tecnologias

- **Backend**: Python 3.11+ com Flask
- **Frontend**: HTML/CSS/JavaScript
- **Banco de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)
- **Hospedagem**: Render

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd comparador-renda-fixa
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
# Crie um arquivo .env
FLASK_ENV=development
SECRET_KEY=sua-chave-secreta-aqui
```

5. Execute o banco de dados:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. Execute a aplicação:
```bash
python run.py
```

A aplicação estará disponível em `http://localhost:5000`

## Criação de Códigos de Acesso

Para criar códigos de acesso, você pode usar o console do Python:

```python
from app import create_app, db
from app.models import AccessCode
from app.utils import gerar_codigo_acesso

app = create_app()
with app.app_context():
    # Gera um código único
    codigo = gerar_codigo_acesso("POTENS")
    
    # Cria o código no banco
    access_code = AccessCode(code=codigo, created_by="Admin")
    db.session.add(access_code)
    db.session.commit()
    
    print(f"Código criado: {codigo}")
```

## Atualização do Boletim Focus

O sistema atualiza automaticamente os dados do Boletim Focus toda segunda-feira às 9h através de um cron job no Render.

A integração usa a **API oficial do BCB** através da biblioteca `python-bcb`:
- API: https://dadosabertos.bcb.gov.br/dataset/expectativas-mercado
- Biblioteca: https://wilsonfreitas.github.io/python-bcb/

Para atualizar manualmente:

```bash
python tasks/update_focus.py
```

Para testar a conexão com a API:

```bash
python -m app.focus_test
```

## Deploy no Render

1. Conecte seu repositório ao Render
2. Configure as variáveis de ambiente:
   - `FLASK_ENV=production`
   - `SECRET_KEY` (gerada automaticamente)
   - `DATABASE_URL` (configurada automaticamente)

3. O Render irá:
   - Instalar dependências automaticamente
   - Criar o banco de dados PostgreSQL
   - Configurar o cron job para atualização do Focus
   - Fazer deploy da aplicação

## Estrutura do Projeto

```
comparador-renda-fixa/
├── app/
│   ├── __init__.py
│   ├── models.py          # Modelos de dados
│   ├── routes.py          # Rotas principais
│   ├── auth.py            # Sistema de autenticação
│   ├── calculations.py    # Cálculos financeiros
│   ├── focus_scraper.py   # Integração com Focus
│   └── utils.py           # Funções auxiliares
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── index.html         # Comparação 1x1
│   ├── compare_multi.html # Comparação 1x vários
│   └── dashboard.html     # Projeções Focus
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── img/
│       └── logo.png       # Coloque seu logo aqui
├── tasks/
│   └── update_focus.py    # Script de atualização Focus
├── requirements.txt
├── config.py
├── run.py
└── render.yaml
```

## Paleta de Cores

- Background claro: `#dadada`
- Texto secundário: `#9a9b9e`
- Destaque/CTA: `#fbb911`
- Texto principal: `#090f3f`
- Bordas/cards: `#4b505b`
- Elementos secundários: `#325157`
- Links/botões: `#016473`

## Licença

Este projeto é propriedade da Potens Investimentos.

# Force rebuild
