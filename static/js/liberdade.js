/* ============================================
   CALCULADORA LIBERDADE FINANCEIRA
   Lógica de cálculo + gráfico + simulações
   ============================================ */

(function () {
    'use strict';

    // ============ HELPERS ============

    function formatBRL(value) {
        if (!isFinite(value)) return 'R$ 0';
        return value.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            maximumFractionDigits: 0
        });
    }

    function parseBRL(str) {
        if (typeof str === 'number') return str;
        if (!str) return 0;
        const cleaned = String(str)
            .replace(/[^\d,.-]/g, '')
            .replace(/\./g, '')
            .replace(',', '.');
        const n = parseFloat(cleaned);
        return isFinite(n) ? n : 0;
    }

    function applyBRLMask(input) {
        input.addEventListener('input', function (e) {
            let raw = e.target.value.replace(/\D/g, '');
            if (!raw) {
                e.target.value = 'R$ 0';
                return;
            }
            const num = parseInt(raw, 10);
            e.target.value = num.toLocaleString('pt-BR', {
                style: 'currency',
                currency: 'BRL',
                maximumFractionDigits: 0
            });
        });
    }

    // ============ IR — AJUSTE DA RENDA DESEJADA ============

    /**
     * Converte renda LÍQUIDA desejada em renda BRUTA necessária.
     * Se a pessoa quer R$ 10.000 líquido com IR de 15%,
     * precisa sacar R$ 11.764,71 bruto.
     *
     * Fórmula: bruto = liquido / (1 - aliquota)
     */
    function aplicarIR(rendaLiquida, aliquotaPct) {
        if (!aliquotaPct || aliquotaPct <= 0) return rendaLiquida;
        if (aliquotaPct >= 100) return Infinity;
        return rendaLiquida / (1 - aliquotaPct / 100);
    }

    // ============ CÁLCULOS FINANCEIROS ============

    function patrimonioNecessario(rendaMensal, taxaRealAA, anosUsufruto) {
        const r = Math.pow(1 + taxaRealAA / 100, 1 / 12) - 1;
        const n = anosUsufruto * 12;
        if (r <= 0) return rendaMensal * n;
        const fator = (1 - Math.pow(1 + r, -n)) / r;
        return rendaMensal * fator;
    }

    function patrimonioAcumulado(pvInicial, aporteMensal, taxaRealAA, meses) {
        const r = Math.pow(1 + taxaRealAA / 100, 1 / 12) - 1;
        if (r <= 0) return pvInicial + aporteMensal * meses;
        const fv = pvInicial * Math.pow(1 + r, meses) +
            aporteMensal * ((Math.pow(1 + r, meses) - 1) / r);
        return fv;
    }

    function mesesParaAtingir(pvInicial, aporteMensal, taxaRealAA, alvo) {
        const r = Math.pow(1 + taxaRealAA / 100, 1 / 12) - 1;
        if (alvo <= pvInicial) return 0;
        if (r <= 0) {
            if (aporteMensal <= 0) return Infinity;
            return Math.ceil((alvo - pvInicial) / aporteMensal);
        }
        const numerador = Math.log((alvo * r + aporteMensal) / (pvInicial * r + aporteMensal));
        const denominador = Math.log(1 + r);
        const n = numerador / denominador;
        return isFinite(n) && n > 0 ? Math.ceil(n) : Infinity;
    }

    function aporteNecessario(pvInicial, alvo, taxaRealAA, meses) {
        if (meses <= 0) return Infinity;
        const r = Math.pow(1 + taxaRealAA / 100, 1 / 12) - 1;
        if (r <= 0) return Math.max(0, (alvo - pvInicial) / meses);
        const fvPV = pvInicial * Math.pow(1 + r, meses);
        const fator = (Math.pow(1 + r, meses) - 1) / r;
        const pmt = (alvo - fvPV) / fator;
        return Math.max(0, pmt);
    }

    // ============ ESTADO ============

    let chartInstance = null;

    // ============ INPUTS ============

    const $ = (id) => document.getElementById(id);

    function lerInputs() {
        const cenarioRadio = document.querySelector('input[name="cenario"]:checked');
        const cenario = cenarioRadio ? cenarioRadio.value : '7';

        let taxa;
        if (cenario === 'custom') {
            taxa = parseFloat($('rentabilidade-custom').value) || 7;
        } else {
            taxa = parseFloat(cenario);
        }

        // ===== IR =====
        const irModo = $('ir-modo') ? $('ir-modo').value : 'bruto';
        let aliquotaIR = 0;

        if (irModo === '15') aliquotaIR = 15;
        else if (irModo === 'isento') aliquotaIR = 0;
        else if (irModo === 'custom') {
            aliquotaIR = parseFloat($('ir-custom').value) || 0;
        }
        // 'bruto' = 0 (não desconta nada)

        return {
            idadeAtual: parseInt($('idade-atual').value, 10) || 30,
            idadeLiberdade: parseInt($('idade-liberdade').value, 10) || 55,
            rendaDesejada: parseBRL($('renda-desejada').value),
            aporteMensal: parseBRL($('aporte-mensal').value),
            patrimonioAtual: parseBRL($('patrimonio-atual').value),
            expectativaVida: parseInt($('expectativa-vida').value, 10) || 90,
            taxaReal: taxa,
            cenario: cenario,
            irModo: irModo,
            aliquotaIR: aliquotaIR
        };
    }

    // ============ RENDER PRINCIPAL ============

    function calcular() {
        const i = lerInputs();

        if (i.idadeLiberdade <= i.idadeAtual) {
            $('result-idade').textContent = '⚠️';
            $('result-status').textContent = 'a idade da liberdade precisa ser maior que a idade atual';
            return;
        }

        const anosAcumulacao = i.idadeLiberdade - i.idadeAtual;
        const mesesAcumulacao = anosAcumulacao * 12;
        const anosUsufruto = Math.max(1, i.expectativaVida - i.idadeLiberdade);

        // ===== AJUSTE DE IR =====
        // A renda que a usuária digitou é o LÍQUIDO desejado.
        // Pra sustentar isso, o saque BRUTO precisa ser maior.
        const rendaBrutaNecessaria = aplicarIR(i.rendaDesejada, i.aliquotaIR);

        // 1. Patrimônio necessário (baseado na renda BRUTA, pois saques são tributados)
        const patrimAlvo = patrimonioNecessario(rendaBrutaNecessaria, i.taxaReal, anosUsufruto);

        // 2. Quanto vai acumular no aporte atual
        const patrimProjetado = patrimonioAcumulado(
            i.patrimonioAtual, i.aporteMensal, i.taxaReal, mesesAcumulacao
        );

        // 3. Quando chega no alvo com o aporte atual?
        const mesesAteAlvo = mesesParaAtingir(
            i.patrimonioAtual, i.aporteMensal, i.taxaReal, patrimAlvo
        );
        const idadeChegada = i.idadeAtual + mesesAteAlvo / 12;

        // 4. Aporte ideal
        const aporteIdeal = aporteNecessario(
            i.patrimonioAtual, patrimAlvo, i.taxaReal, mesesAcumulacao
        );

        // ===== RENDER =====
        $('result-patrimonio').textContent = formatBRL(patrimAlvo);
        $('result-projetado').textContent = formatBRL(patrimProjetado);
        $('result-aporte-ideal').textContent = formatBRL(aporteIdeal);

        document.getElementById('label-projetado').textContent =
            `Para chegar lá na idade que você escolheu (${i.idadeLiberdade} anos)`;
        document.getElementById('label-projetado-patrimonio').textContent =
            `Aos ${i.idadeLiberdade} anos`;


        // ===== AVISO IR =====
        atualizarAvisoIR(i);

        const statusEl = $('result-status');
        const idadeEl = $('result-idade');

        if (!isFinite(idadeChegada) || idadeChegada > 120) {
            idadeEl.textContent = '😬';
            statusEl.textContent = 'com esse aporte, não chega lá';
            statusEl.className = 'lib-headline-note lib-status-fail';
        } else if (idadeChegada <= i.idadeLiberdade) {
            idadeEl.textContent = `aos ${Math.ceil(idadeChegada)} anos`;
            statusEl.textContent = '🎉 você chega antes do planejado!';
            statusEl.className = 'lib-headline-note lib-status-ok';
        } else {
            const atraso = Math.ceil(idadeChegada - i.idadeLiberdade);
            idadeEl.textContent = `aos ${Math.ceil(idadeChegada)} anos`;
            statusEl.textContent = `${atraso} ano(s) depois do planejado`;
            statusEl.className = 'lib-headline-note lib-status-fail';
        }

        // ===== GRÁFICO =====
        renderizarGrafico(i, patrimAlvo, mesesAcumulacao);

        // ===== E SE EU AJUSTAR =====
        renderizarSimulacoes(i, patrimAlvo, mesesAcumulacao, idadeChegada, aporteIdeal);
    }

    // ============ AVISO IR ============

    function atualizarAvisoIR(i) {
        const avisoEl = $('ir-note');
        if (!avisoEl) return;

        if (i.irModo === 'bruto') {
            avisoEl.classList.remove('lib-ir-applied');
            avisoEl.innerHTML = `
                ⚠️ Cálculo bruto, sem descontar IR.
                <a href="#" id="ir-link">Ajustar nas opções avançadas</a>
            `;
            // re-amarrar evento de clique
            const link = $('ir-link');
            if (link) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const details = document.querySelector('.lib-advanced');
                    if (details) {
                        details.open = true;
                        details.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        setTimeout(() => $('ir-modo').focus(), 400);
                    }
                });
            }
        } else if (i.irModo === 'isento') {
            avisoEl.classList.remove('lib-ir-applied');
            avisoEl.innerHTML = `✅ Considerando carteira <strong>isenta de IR</strong> (LCI, LCA, debêntures incentivadas).`;
        } else {
            avisoEl.classList.remove('lib-ir-applied');
            avisoEl.innerHTML = `✅ Considerando <strong>${i.aliquotaIR}% de IR</strong> sobre os saques.`;
        }
    }

    // ============ GRÁFICO ============

    function renderizarGrafico(i, patrimAlvo, mesesAcumulacao) {
        const ctx = $('lib-chart').getContext('2d');

        const labels = [];
        const dadosPatrimonio = [];
        const dadosAlvo = [];

        for (let ano = 0; ano <= (mesesAcumulacao / 12); ano++) {
            labels.push(`${i.idadeAtual + ano}`);
            const meses = ano * 12;
            const fv = patrimonioAcumulado(
                i.patrimonioAtual, i.aporteMensal, i.taxaReal, meses
            );
            dadosPatrimonio.push(Math.round(fv));
            dadosAlvo.push(Math.round(patrimAlvo));
        }

        if (chartInstance) chartInstance.destroy();

        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Seu patrimônio projetado',
                        data: dadosPatrimonio,
                        borderColor: '#0033a0',
                        backgroundColor: 'rgba(0, 51, 160, 0.1)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 3,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Patrimônio necessário',
                        data: dadosAlvo,
                        borderColor: '#ffd300',
                        backgroundColor: 'transparent',
                        borderDash: [8, 4],
                        fill: false,
                        tension: 0,
                        borderWidth: 2,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { font: { size: 13 }, padding: 14 }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${formatBRL(ctx.parsed.y)}`,
                            title: (items) => `Aos ${items[0].label} anos`
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: (v) => {
                                if (v >= 1e6) return 'R$ ' + (v / 1e6).toFixed(1) + 'M';
                                if (v >= 1e3) return 'R$ ' + (v / 1e3).toFixed(0) + 'k';
                                return 'R$ ' + v;
                            }
                        },
                        grid: { color: 'rgba(0, 51, 160, 0.06)' }
                    },
                    x: {
                        title: { display: true, text: 'Sua idade', font: { size: 12 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // ============ E SE EU AJUSTAR ============

    function renderizarSimulacoes(i, patrimAlvo, mesesAcumulacao, idadeChegada, aporteIdeal) {
        // 1. Adiar 5 anos
        const mesesMais5 = mesesAcumulacao + 60;
        const aporteSeAdiar = aporteNecessario(i.patrimonioAtual, patrimAlvo, i.taxaReal, mesesMais5);
        const economia = Math.max(0, i.aporteMensal - aporteSeAdiar);
        $('text-adiar').innerHTML = isFinite(aporteSeAdiar)
            ? `Se você <strong>adiar 5 anos</strong> (até os ${i.idadeLiberdade + 5}), o aporte cai pra <strong>${formatBRL(aporteSeAdiar)}/mês</strong>${economia > 0 ? ` — alívio de ${formatBRL(economia)}/mês.` : '.'}`
            : `Adiar 5 anos não muda o cenário com esses números.`;

        // 2. Aumentar aporte em 50%
        const aporteMais50 = i.aporteMensal * 1.5;
        const mesesComMais = mesesParaAtingir(i.patrimonioAtual, aporteMais50, i.taxaReal, patrimAlvo);
        const idadeComMais = i.idadeAtual + mesesComMais / 12;
        $('text-aumentar').innerHTML = isFinite(idadeComMais) && idadeComMais < 120
            ? `Se você <strong>aumentar o aporte em 50%</strong> (${formatBRL(aporteMais50)}/mês), chega aos <strong>${Math.ceil(idadeComMais)} anos</strong>.`
            : `Mesmo aumentando 50%, ainda fica longe. Vale revisar a renda desejada.`;

        // 3. Reduzir renda desejada em 20%
        const rendaMenor = i.rendaDesejada * 0.8;
        const rendaMenorBruta = aplicarIR(rendaMenor, i.aliquotaIR);
        const patrimMenor = patrimonioNecessario(rendaMenorBruta, i.taxaReal, i.expectativaVida - i.idadeLiberdade);
        const mesesMenor = mesesParaAtingir(i.patrimonioAtual, i.aporteMensal, i.taxaReal, patrimMenor);
        const idadeMenor = i.idadeAtual + mesesMenor / 12;
        $('text-reduzir').innerHTML = isFinite(idadeMenor) && idadeMenor < 120
            ? `Se você <strong>reduzir a renda alvo em 20%</strong> (${formatBRL(rendaMenor)}/mês), chega aos <strong>${Math.ceil(idadeMenor)} anos</strong>.`
            : `Mesmo reduzindo 20% da renda alvo, o aporte atual não alcança.`;
    }

    // ============ INIT ============

    function init() {
        // máscaras BRL
        ['renda-desejada', 'aporte-mensal', 'patrimonio-atual'].forEach(id => {
            const el = $(id);
            if (el) applyBRLMask(el);
        });

        // toggle rentabilidade custom
        document.querySelectorAll('input[name="cenario"]').forEach(radio => {
            radio.addEventListener('change', () => {
                const wrapper = $('custom-rate-wrapper');
                const isCustom = document.querySelector('input[name="cenario"]:checked').value === 'custom';
                wrapper.hidden = !isCustom;
                if (isCustom) {
                    const details = document.querySelector('.lib-advanced');
                    if (details) details.open = true;
                }
                calcular();
            });
        });

        // toggle IR custom
        const irModoEl = $('ir-modo');
        if (irModoEl) {
            irModoEl.addEventListener('change', () => {
                const wrapper = $('ir-custom-wrapper');
                wrapper.hidden = irModoEl.value !== 'custom';
                calcular();
            });
        }

        // recálculo em qualquer input
        document.querySelectorAll('#lib-form input, #lib-form select').forEach(input => {
            input.addEventListener('input', () => {
                clearTimeout(window.__libDebounce);
                window.__libDebounce = setTimeout(calcular, 250);
            });
        });

        // primeiro cálculo
        calcular();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
