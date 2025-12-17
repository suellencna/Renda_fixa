# Guia de Deploy no Railway

Este guia explica como fazer o deploy da aplicação no Railway.

## Pré-requisitos

1. Conta no Railway (https://railway.app)
2. Git configurado no projeto
3. Código commitado no repositório

## Passos para Deploy

### 1. Criar Novo Projeto no Railway

1. Acesse https://railway.app e faça login
2. Clique em "New Project"
3. Selecione "Deploy from GitHub repo" (recomendado) ou "Empty Project"

### 2. Configurar Variáveis de Ambiente

No painel do Railway, vá em "Variables" e adicione as seguintes variáveis:

#### Obrigatórias:
- `FLASK_ENV=production`
- `SECRET_KEY` - Gere uma chave secreta forte (ex: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL` - Será criada automaticamente se você adicionar um serviço PostgreSQL

#### Opcionais (com valores padrão):
- `ACCESS_CODE_DEFAULT` - Código de acesso padrão (padrão: 'REALIZAR-1A73')
- `ADMIN_EMAILS` - Emails de administradores separados por vírgula (padrão: 'suellencna@gmail.com')

### 3. Adicionar Banco de Dados PostgreSQL

1. No projeto Railway, clique em "New"
2. Selecione "Database" → "Add PostgreSQL"
3. O Railway criará automaticamente a variável `DATABASE_URL`

### 4. Executar Migrações do Banco de Dados

Após o deploy, você precisará executar as migrações:

1. No Railway, vá em "Deployments"
2. Clique nos três pontos do deployment mais recente
3. Selecione "Open Shell"
4. Execute:
   ```bash
   flask db upgrade
   ```

Ou configure um comando de setup no Railway para executar automaticamente.

### 5. Configurar Domínio (Opcional)

1. No projeto Railway, vá em "Settings"
2. Em "Domains", clique em "Generate Domain"
3. Ou adicione seu domínio personalizado

## Estrutura de Arquivos

Os seguintes arquivos são importantes para o deploy:

- `Procfile` - Define o comando de inicialização (gunicorn)
- `requirements.txt` - Dependências Python
- `runtime.txt` - Versão do Python
- `railway.json` - Configurações do Railway
- `run.py` - Arquivo principal da aplicação

## Verificação

Após o deploy, verifique:

1. ✅ A aplicação está rodando (status "Active")
2. ✅ Os logs não mostram erros
3. ✅ O banco de dados está conectado
4. ✅ As rotas estão acessíveis

## Troubleshooting

### Erro de conexão com banco de dados
- Verifique se a variável `DATABASE_URL` está configurada
- Confirme que o serviço PostgreSQL está ativo

### Erro 500 na aplicação
- Verifique os logs no Railway
- Confirme que todas as variáveis de ambiente estão configuradas
- Verifique se as migrações foram executadas

### Aplicação não inicia
- Verifique se o `Procfile` está correto
- Confirme que o `gunicorn` está no `requirements.txt`
- Verifique os logs de build

## Comandos Úteis

```bash
# Ver logs em tempo real
railway logs

# Abrir shell no Railway
railway shell

# Executar migrações
railway run flask db upgrade
```
