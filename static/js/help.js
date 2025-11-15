document.addEventListener('DOMContentLoaded', () => {
    const tooltip = document.createElement('div');
    tooltip.className = 'help-tooltip';
    document.body.appendChild(tooltip);

    let tooltipTimeout;

    function hideTooltip() {
        tooltip.classList.remove('visible');
    }

    function showTooltip(target) {
        const text = target.getAttribute('data-help');
        if (!text) {
            return;
        }
        tooltip.textContent = text;
        tooltip.classList.add('visible');
        const rect = target.getBoundingClientRect();
        const top = rect.bottom + window.scrollY + 10;
        const left = rect.left + window.scrollX - tooltip.offsetWidth / 2 + rect.width / 2;
        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${Math.max(12, left)}px`;

        clearTimeout(tooltipTimeout);
        tooltipTimeout = setTimeout(hideTooltip, 7000);
    }

    document.body.addEventListener('click', (event) => {
        const icon = event.target.closest('.help-icon');
        if (icon) {
            event.preventDefault();
            showTooltip(icon);
        } else if (!event.target.closest('.help-tooltip')) {
            hideTooltip();
        }
    });

    const mainHelpBtn = document.getElementById('help-main-btn');
    const helpMenu = document.getElementById('help-floating-menu');

    mainHelpBtn?.addEventListener('click', (event) => {
        event.preventDefault();
        helpMenu?.classList.toggle('open');
    });

    document.addEventListener('click', (event) => {
        if (
            !event.target.closest('#help-floating-menu') &&
            !event.target.closest('#help-main-btn')
        ) {
            helpMenu?.classList.remove('open');
        }
    });

    // Help panel
    const helpPanel = document.getElementById('help-panel');
    const openHelpButtons = document.querySelectorAll('[data-open-help]');
    const closeHelpBtn = document.getElementById('help-panel-close');

    openHelpButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (helpPanel) {
                helpPanel.classList.add('open');
                helpMenu?.classList.remove('open');
            }
        });
    });

    closeHelpBtn?.addEventListener('click', () => helpPanel.classList.remove('open'));

    helpPanel?.addEventListener('click', (event) => {
        if (event.target === helpPanel) {
            helpPanel.classList.remove('open');
        }
    });

    // Guided tour
    const tourButtons = document.querySelectorAll('[data-start-tour]');
    const tourSteps = [...document.querySelectorAll('[data-tour-step]')].sort(
        (a, b) => Number(a.dataset.tourStep) - Number(b.dataset.tourStep)
    );

    if (tourSteps.length) {
        const overlay = document.createElement('div');
        overlay.className = 'tour-overlay';
        const popup = document.createElement('div');
        popup.className = 'tour-popup';
        const counter = document.createElement('span');
        counter.className = 'tour-counter';
        const textEl = document.createElement('p');
        const controls = document.createElement('div');
        controls.className = 'tour-controls';
        const btnNext = document.createElement('button');
        btnNext.className = 'btn btn-primary';
        btnNext.textContent = 'Próximo';
        const btnSkip = document.createElement('button');
        btnSkip.className = 'btn btn-secondary';
        btnSkip.textContent = 'Sair';

        controls.append(btnSkip, btnNext);
        popup.append(counter, textEl, controls);
        overlay.appendChild(popup);
        document.body.appendChild(overlay);

        let stepIndex = 0;

        function highlightStep() {
            const stepElement = tourSteps[stepIndex];
            if (!stepElement) {
                overlay.classList.remove('visible');
                document.body.classList.remove('tour-active');
                tourSteps.forEach(el => el.classList.remove('tour-highlight'));
                return;
            }
            document.body.classList.add('tour-active');
            overlay.classList.add('visible');
            tourSteps.forEach(el => el.classList.remove('tour-highlight'));
            stepElement.classList.add('tour-highlight');
            const total = tourSteps.length;
            counter.textContent = `Passo ${stepIndex + 1} de ${total}`;
            textEl.textContent = stepElement.dataset.tourText || '';
            const rect = stepElement.getBoundingClientRect();
            popup.style.top = `${rect.bottom + window.scrollY + 20}px`;
            popup.style.left = `${rect.left + window.scrollX}px`;
        }

        function startTour() {
            stepIndex = 0;
            highlightStep();
        }

        btnNext.addEventListener('click', () => {
            stepIndex += 1;
            if (stepIndex >= tourSteps.length) {
                overlay.classList.remove('visible');
                document.body.classList.remove('tour-active');
                tourSteps.forEach(el => el.classList.remove('tour-highlight'));
            } else {
                highlightStep();
            }
        });

        btnSkip.addEventListener('click', () => {
            overlay.classList.remove('visible');
            document.body.classList.remove('tour-active');
            tourSteps.forEach(el => el.classList.remove('tour-highlight'));
        });

        tourButtons.forEach(btn => btn.addEventListener('click', (event) => {
            event.preventDefault();
            helpMenu?.classList.remove('open');
            startTour();
        }));
    }
});

