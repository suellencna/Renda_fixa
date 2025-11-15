document.addEventListener('DOMContentLoaded', () => {
    const btnSimular = document.getElementById('btn-simular');
    if (!btnSimular) {
        return;
    }
    
    const resultadosContainer = document.getElementById('resultados-gerais');
    const listaResultados = document.getElementById('lista-resultados');
    const tabelaDetalhes = document.getElementById('tabela-detalhes');
    const tabelaCorpo = document.getElementById('tabela-corpo');
    const totalInvestidoSpan = document.getElementById('total-investido');
    const btnVerTabela = document.getElementById('btn-ver-tabela');
    const canvasGrafico = document.getElementById('grafico-evolucao');
    const graficoContainer = document.querySelector('.grafico-container');
    let graficoEvolucao = null;
    
    const camposParametros = {
        selic: document.getElementById('param-selic'),
        cdi: document.getElementById('param-cdi'),
        ipca: document.getElementById('param-ipca'),
        tr: document.getElementById('param-tr'),
        taxa_custodia: document.getElementById('param-custodia'),
        tesouro_prefixado_nominal: document.getElementById('param-tesouro-prefixado'),
        tesouro_ipca_mais: document.getElementById('param-tesouro-ipca'),
        taxa_admin_fundo_di: document.getElementById('param-admin-fundo'),
        rentabilidade_cdb: document.getElementById('param-rent-cdb'),
        rentabilidade_fundo_di: document.getElementById('param-rent-fundo'),
        rentabilidade_lci_lca: document.getElementById('param-rent-lci'),
        poupanca_mensal: document.getElementById('param-poupanca')
    };
    
    // Preenche campos com defaults via JS (garantia extra)
    if (typeof defaultParams === 'object') {
        Object.entries(camposParametros).forEach(([chave, campo]) => {
            if (campo && defaultParams[chave] !== undefined && campo.value === '') {
                campo.value = defaultParams[chave];
            }
        });
    }
    
    function coletarParametros() {
        const params = {};
        Object.entries(camposParametros).forEach(([chave, campo]) => {
            params[chave] = parseFloat(campo.value.replace(',', '.')) || 0;
        });
        return params;
    }
    
    function obterTaxRegime() {
        const selecionado = document.querySelector('input[name="tax-regime"]:checked');
        return selecionado ? selecionado.value : '2025';
    }
    
    function montarPayload() {
        const valorInicial = parseFloat(document.getElementById('input-valor-inicial').value) || 0;
        const aporte = parseFloat(document.getElementById('input-aporte').value) || 0;
        const meses = parseInt(document.getElementById('input-prazo').value, 10) || 0;
        
        return {
            valor_inicial: valorInicial,
            aportes_mensais: aporte,
            meses,
            parametros: coletarParametros(),
            incluir_ir: document.getElementById('chk-ir').checked,
            ajustar_inflacao: document.getElementById('chk-inflacao').checked,
            tax_regime: obterTaxRegime()
        };
    }
    
    function validarEntrada(payload) {
        if (payload.valor_inicial <= 0) {
            alert('Informe um valor inicial maior que zero.');
            return false;
        }
        if (payload.meses <= 0) {
            alert('Informe um período (em meses) maior que zero.');
            return false;
        }
        return true;
    }
    
    function atualizarResumo(resultados) {
        const ordenados = [...resultados].sort((a, b) => b.valor_liquido - a.valor_liquido);
        const maiorValor = ordenados.length ? ordenados[0].valor_liquido : 0;
        listaResultados.innerHTML = '';
        
        ordenados.forEach((resultado) => {
            const item = document.createElement('div');
            item.className = 'resultado-item';
            
            const progresso = document.createElement('div');
            progresso.className = 'barra-progresso';
            
            const preenchimento = document.createElement('div');
            preenchimento.className = 'barra-preenchimento';
            const percentual = maiorValor ? (resultado.valor_liquido / maiorValor) * 100 : 0;
            preenchimento.style.width = `${percentual}%`;
            
            progresso.appendChild(preenchimento);
            
            const valorSpan = document.createElement('span');
            valorSpan.className = 'resultado-valor';
            valorSpan.textContent = formatarMoeda(resultado.valor_liquido);
            
            const nome = document.createElement('strong');
            nome.textContent = resultado.nome;
            
            item.appendChild(nome);
            item.appendChild(progresso);
            item.appendChild(valorSpan);
            listaResultados.appendChild(item);
        });
        
        if (ordenados.length > 0) {
            totalInvestidoSpan.textContent = formatarMoeda(ordenados[0].total_investido);
        }
        
        resultadosContainer.style.display = 'block';
    }
    
    function atualizarTabela(resultados) {
        tabelaCorpo.innerHTML = '';
        resultados.forEach((resultado) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${resultado.nome}</strong></td>
                <td>${formatarMoeda(resultado.valor_bruto)}</td>
                <td>${formatarPorcentagem(resultado.rentabilidade_bruta)}</td>
                <td>${formatarMoeda(resultado.custos)}</td>
                <td>${formatarMoeda(resultado.valor_ir)}</td>
                <td>${formatarMoeda(resultado.valor_liquido)}</td>
                <td>${formatarPorcentagem(resultado.rentabilidade_liquida)}</td>
                <td>${formatarMoeda(resultado.ganho_liquido)}</td>
            `;
            tabelaCorpo.appendChild(tr);
        });
    }
    
    btnSimular.addEventListener('click', async () => {
        const payload = montarPayload();
        
        if (!validarEntrada(payload)) {
            return;
        }
        
        btnSimular.disabled = true;
        const textoOriginal = btnSimular.textContent;
        btnSimular.textContent = 'Calculando...';
        
        try {
            const resposta = await fetch('/api/simular-renda-fixa', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (!resposta.ok) {
                const erro = await resposta.json();
                throw new Error(erro.error || 'Não foi possível realizar a simulação.');
            }
            
            const dados = await resposta.json();
            const resultados = dados.resultados || [];
            
            atualizarResumo(resultados);
            atualizarTabela(resultados);
            atualizarGrafico(resultados);
            tabelaDetalhes.style.display = 'none';
            
        } catch (erro) {
            console.error(erro);
            alert(erro.message);
        } finally {
            btnSimular.disabled = false;
            btnSimular.textContent = textoOriginal;
        }
    });
    
    if (btnVerTabela) {
        btnVerTabela.addEventListener('click', () => {
            tabelaDetalhes.style.display = tabelaDetalhes.style.display === 'none' ? 'block' : 'none';
            btnVerTabela.textContent = tabelaDetalhes.style.display === 'none' ? 'Ver simulação completa' : 'Ocultar tabela';
        });
    }
    
    function atualizarGrafico(resultados) {
        if (!canvasGrafico) return;

        if (graficoContainer) {
            graficoContainer.style.display = 'none';
        }
        
        const ativosComEvolucao = resultados
            .filter(r => Array.isArray(r.evolucao_mensal) && r.evolucao_mensal.length > 0)
            .sort((a, b) => b.valor_liquido - a.valor_liquido);
        
        if (ativosComEvolucao.length === 0) {
            if (graficoEvolucao) {
                graficoEvolucao.destroy();
                graficoEvolucao = null;
            }
            return;
        }

        if (graficoContainer) {
            graficoContainer.style.display = 'block';
        }
        
        const primeiro = ativosComEvolucao[0];
        const meses = primeiro.evolucao_mensal.map(e => e.mes);
        
        const hoje = new Date();
        const labels = meses.map(mes => {
            const data = new Date(hoje);
            data.setMonth(hoje.getMonth() + mes - 1);
            const mesStr = String(data.getMonth() + 1).padStart(2, '0');
            const anoStr = String(data.getFullYear()).slice(-2);
            return `${mesStr}/${anoStr}`;
        });
        
        const coresPadrao = [
            '#0033a0',
            '#dc3545',
            '#28a745',
            '#6f42c1',
            '#f39c12',
            '#16a085',
            '#8e44ad',
            '#e91e63',
            '#2c3e50',
            '#ff6f00'
        ];
        
        const datasets = ativosComEvolucao.map((resultado, index) => {
            let corLinha;
            let corArea;
            
            if (index < coresPadrao.length) {
                corLinha = coresPadrao[index];
                corArea = `${corLinha}33`;
            } else {
                const hue = (index * 47) % 360;
                corLinha = `hsl(${hue}, 70%, 45%)`;
                corArea = `hsla(${hue}, 70%, 45%, 0.2)`;
            }
            
            return {
                label: resultado.nome,
                data: resultado.evolucao_mensal.map(e => e.valor_liquido),
                borderColor: corLinha,
                backgroundColor: corArea,
                pointBackgroundColor: corLinha,
                pointBorderColor: '#ffffff',
                borderWidth: 2,
                fill: false,
                tension: 0.15
            };
        });
        
        if (graficoEvolucao) {
            graficoEvolucao.destroy();
        }
        
        graficoEvolucao = new Chart(canvasGrafico, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                            font: {
                                size: 12,
                                weight: '500'
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 10,
                        titleFont: {
                            size: 13,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 12
                        },
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${formatarMoeda(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return formatarMoeda(value);
                            },
                            font: {
                                size: 11
                            },
                            padding: 8
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.08)',
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            padding: 8
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                elements: {
                    point: {
                        radius: 3,
                        hoverRadius: 5,
                        borderWidth: 2
                    },
                    line: {
                        borderWidth: 2
                    }
                }
            }
        });
    }
});

