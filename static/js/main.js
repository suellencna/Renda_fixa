// Funções principais do comparador de renda fixa

// Glossário de termos
const glossary = {
    'cdb': 'CDB (Certificado de Depósito Bancário) é um título de renda fixa emitido por bancos. Você empresta dinheiro ao banco e recebe juros em troca. É protegido pelo FGC até R$ 250 mil.',
    'lci': 'LCI (Letra de Crédito Imobiliário) é um título de renda fixa ligado ao setor imobiliário. É isento de Imposto de Renda e protegido pelo FGC até R$ 250 mil.',
    'lca': 'LCA (Letra de Crédito do Agronegócio) é um título de renda fixa ligado ao agronegócio. É isento de Imposto de Renda e protegido pelo FGC até R$ 250 mil.',
    'tesouro_selic': 'Tesouro Selic é um título público do governo federal. Sua rentabilidade acompanha a taxa Selic (taxa básica de juros).',
    'tesouro_ipca': 'Tesouro IPCA+ é um título público que protege seu dinheiro da inflação, rendendo IPCA mais uma taxa fixa.',
    'tesouro_prefixado': 'Tesouro Prefixado é um título público com taxa de juros conhecida desde o início. Você sabe exatamente quanto vai render.',
    'fundo_di': 'Fundo DI investe em títulos públicos que acompanham a taxa DI, muito próxima da Selic. É uma forma de investir em renda fixa através de um fundo.',
    'debenture': 'Debênture é um título de dívida emitido por empresas privadas. As comuns pagam IR conforme o prazo.',
    'debenture_incentivada': 'Debênture incentivada financia projetos de infraestrutura e é isenta de IR até 2025; com a MP 1.303/2025 passa a ter alíquota reduzida.',
    'prefixado': 'Pré-fixado significa que a taxa de juros é conhecida desde o início. Exemplo: 10% ao ano.',
    'cdi': 'CDI (Certificado de Depósito Interbancário) é uma taxa de juros muito próxima da Selic. Quando um investimento rende "X% do CDI", significa que rende uma porcentagem dessa taxa.',
    'ipca_mais': 'IPCA+ significa que o investimento rende a inflação (IPCA) mais uma taxa fixa. Exemplo: IPCA + 5% significa que você ganha a inflação mais 5% ao ano.',
    'ir': 'IR (Imposto de Renda) é cobrado sobre o ganho do investimento. A alíquota diminui conforme o tempo de investimento (tabela regressiva).',
    'ipca': 'IPCA (Índice Nacional de Preços ao Consumidor Amplo) é o índice oficial de inflação no Brasil. Mede quanto os preços subiram.'
};

// Função para formatar moeda
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

// Função para formatar porcentagem
function formatarPorcentagem(valor) {
    return valor.toFixed(2) + '%';
}

// Função para mostrar tooltip do glossário
function mostrarGlossario(termo) {
    const modal = document.getElementById('glossary-modal');
    const content = document.getElementById('glossary-content');
    
    if (glossary[termo]) {
        content.innerHTML = `<h3>${termo.toUpperCase()}</h3><p>${glossary[termo]}</p>`;
        modal.style.display = 'block';
    }
}

// Fechar modal
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('glossary-modal');
    const closeBtn = document.querySelector('.modal-close');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
    
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// Função para calcular investimento
async function calcularInvestimento(investmentData) {
    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(investmentData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro ao calcular investimento');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro:', error);
        throw error;
    }
}

// Função para exibir resultados
function exibirResultado(containerId, resultado, titulo) {
    const container = document.getElementById(containerId);
    const content = container.querySelector('.result-content');
    
    content.innerHTML = `
        <div class="result-item">
            <span class="result-label">Total Investido:</span>
            <span class="result-value">${formatarMoeda(resultado.total_investido)}</span>
        </div>
        <div class="result-item">
            <span class="result-label">Valor Bruto:</span>
            <span class="result-value">${formatarMoeda(resultado.valor_bruto)}</span>
        </div>
        <div class="result-item">
            <span class="result-label">Rentabilidade Bruta:</span>
            <span class="result-value">${formatarPorcentagem(resultado.rentabilidade_bruta)}</span>
        </div>
        ${resultado.custos > 0 ? `
        <div class="result-item">
            <span class="result-label">Custos:</span>
            <span class="result-value">${formatarMoeda(resultado.custos)}</span>
        </div>
        ` : ''}
        ${resultado.valor_ir > 0 ? `
        <div class="result-item">
            <span class="result-label">Imposto de Renda:</span>
            <span class="result-value">${formatarMoeda(resultado.valor_ir)}</span>
        </div>
        ` : ''}
        <div class="result-item">
            <span class="result-label">Valor Líquido:</span>
            <span class="result-value" style="color: var(--color-link); font-size: 1.3rem;">${formatarMoeda(resultado.valor_liquido)}</span>
        </div>
        <div class="result-item">
            <span class="result-label">Rentabilidade Líquida:</span>
            <span class="result-value" style="color: var(--color-success);">${formatarPorcentagem(resultado.rentabilidade_liquida)}</span>
        </div>
        <div class="result-item">
            <span class="result-label">Ganho Líquido:</span>
            <span class="result-value" style="color: var(--color-success); font-size: 1.2rem;">${formatarMoeda(resultado.ganho_liquido)}</span>
        </div>
        ${resultado.ganho_real !== undefined ? `
        <div class="result-item">
            <span class="result-label">Ganho Real (ajustado pela inflação):</span>
            <span class="result-value">${formatarMoeda(resultado.ganho_real)}</span>
        </div>
        ` : ''}
    `;
}

// Event listener para botão calcular (comparação 1x1)
document.addEventListener('DOMContentLoaded', function() {
    const btnCalcular = document.getElementById('btn-calcular');
    
    if (btnCalcular) {
        btnCalcular.addEventListener('click', async function() {
            const sharedForm = document.getElementById('shared-form');
            const form1 = document.querySelector('form[data-investment="1"]');
            const form2 = document.querySelector('form[data-investment="2"]');
            
            if (!sharedForm || !form1 || !form2) {
                alert('Erro: Formulários não encontrados');
                return;
            }
            
            // Valida formulários
            if (!sharedForm.checkValidity() || !form1.checkValidity() || !form2.checkValidity()) {
                alert('Por favor, preencha todos os campos obrigatórios');
                sharedForm.reportValidity();
                form1.reportValidity();
                form2.reportValidity();
                return;
            }
            
            const valorInicialInput = document.getElementById('valor_inicial_compartilhado');
            const aportesInput = document.getElementById('aportes_compartilhados');
            const prazoInput = document.getElementById('prazo_compartilhado');

            const valorInicial = parseFloat(valorInicialInput.value);
            const aportesMensais = parseFloat(aportesInput.value) || 0;
            const meses = parseInt(prazoInput.value, 10);

            // Coleta dados
            const incluirIR = document.getElementById('incluir_ir').checked;
            const ajustarInflacao = document.getElementById('ajustar_inflacao').checked;
            const taxRegimeInput = document.querySelector('input[name="tax_regime"]:checked');
            const taxRegime = taxRegimeInput ? taxRegimeInput.value : '2025';
            
            const data1 = {
                investimento_type: form1.querySelector('[name="investimento_type"]').value,
                rentabilidade_type: form1.querySelector('[name="rentabilidade_type"]').value,
                rentabilidade_value: parseFloat(form1.querySelector('[name="rentabilidade_value"]').value),
                valor_inicial: valorInicial,
                aportes_mensais: aportesMensais,
                meses,
                incluir_ir: incluirIR,
                ajustar_inflacao: ajustarInflacao,
                tax_regime: taxRegime
            };
            
            const data2 = {
                investimento_type: form2.querySelector('[name="investimento_type"]').value,
                rentabilidade_type: form2.querySelector('[name="rentabilidade_type"]').value,
                rentabilidade_value: parseFloat(form2.querySelector('[name="rentabilidade_value"]').value),
                valor_inicial: valorInicial,
                aportes_mensais: aportesMensais,
                meses,
                incluir_ir: incluirIR,
                ajustar_inflacao: ajustarInflacao,
                tax_regime: taxRegime
            };
            
            // Desabilita botão
            btnCalcular.disabled = true;
            btnCalcular.textContent = 'Calculando...';
            
            try {
                // Calcula ambos
                const [resultado1, resultado2] = await Promise.all([
                    calcularInvestimento(data1),
                    calcularInvestimento(data2)
                ]);
                
                // Exibe resultados
                exibirResultado('result-1', resultado1, 'Investimento 1');
                exibirResultado('result-2', resultado2, 'Investimento 2');
                
                // Mostra container de resultados
                document.getElementById('results-container').style.display = 'block';
                
                // Scroll para resultados
                document.getElementById('results-container').scrollIntoView({ behavior: 'smooth' });
                
            } catch (error) {
                alert('Erro ao calcular: ' + error.message);
            } finally {
                btnCalcular.disabled = false;
                btnCalcular.textContent = 'Calcular Comparação';
            }
        });
    }
});




