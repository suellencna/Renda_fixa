#!/usr/bin/env python3
"""
Atualiza as principais taxas utilizadas no comparador de ativos.

O script busca as séries públicas do Banco Central via API SGS e gera
um arquivo JSON em `data/taxas.json` com todas as informações mais recentes.

Além disso, calcula algumas métricas derivadas (rentabilidades de CDB,
LCI/LCA, fundos DI e poupança) com base nas taxas coletadas.

Uso:
    python scripts/update_rates.py             # roda apenas no dia útil pós-Copom
    python scripts/update_rates.py --force     # força a atualização em qualquer dia
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import requests


# Datas oficiais das reuniões do Copom (2025-2026). Sempre revisitar
# quando o Banco Central publicar um novo calendário.
COPOM_DATES = [
    date(2025, 12, 10),
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 8, 5),
    date(2026, 9, 16),
    date(2026, 11, 4),
    date(2026, 12, 9),
]

SGS_SERIES = {
    "selic_meta": 432,
    "cdi_over": 4389,
    "ipca_12m": 13522,
    "ipca_mensal": 433,
    "tr_mensal": 226,
}

OUTPUT_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    .joinpath("data", "taxas.json")
)
LOG_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    .joinpath("data", "taxas.log")
)


def is_business_day(target: date) -> bool:
    """Retorna True se for dia útil (segunda a sexta)."""
    return target.weekday() < 5


def should_update_today(today: date) -> bool:
    """Verifica se hoje é o dia útil imediatamente após uma reunião do Copom."""
    if not is_business_day(today):
        return False
    return any(today == meeting + timedelta(days=1) for meeting in COPOM_DATES)


def fetch_sgs_series(series_id: int) -> Optional[float]:
    """Busca a última observação de uma série SGS do Banco Central."""
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}/"
        "dados/ultimos/1?formato=json"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        valor = data[0]["valor"].replace(",", ".")
        return float(valor)
    except Exception as exc:  # pragma: no cover - tratamos genericamente
        logging.exception("Falha ao buscar série %s: %s", series_id, exc)
        return None


def compute_derived_metrics(rates: Dict[str, Optional[float]]) -> Dict[str, float]:
    """Calcula métricas derivadas com base nas taxas coletadas."""
    derived: Dict[str, float] = {}

    cdi = rates.get("cdi_over")
    tr_mensal = rates.get("tr_mensal")

    if cdi is not None:
        derived["cdb_100_cdi_bruto_anual"] = cdi
        # IR regressivo para 12 meses (alíquota de 17.5%)
        derived["cdb_100_cdi_liquido_12m"] = cdi * (1 - 0.175)
        derived["lci_lca_85_cdi"] = cdi * 0.85  # isentas de IR
        # Rentabilidade líquida aproximada de fundos DI com taxa de adm de 0.25% a.a.
        derived["fundo_di_liquido"] = max(cdi - 0.25, 0)
    if tr_mensal is not None:
        # Poupança rende 0.5% ao mês + TR quando Selic >= 8.5% a.a.
        poupanca_mensal = 0.5 + tr_mensal
        derived["poupanca_mensal"] = poupanca_mensal
        derived["poupanca_anual_aprox"] = ((1 + poupanca_mensal / 100) ** 12 - 1) * 100

    return derived


def write_rates(payload: Dict[str, Optional[float]]) -> None:
    """Grava o dicionário de taxas em JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def configure_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def main(force: bool = False) -> None:
    configure_logging()

    today = date.today()
    if not force and not should_update_today(today):
        logging.info("Execução ignorada (fora da janela pós-Copom).")
        return

    logging.info("Iniciando atualização das taxas (force=%s).", force)

    rates: Dict[str, Optional[float]] = {"data_atualizacao": today.isoformat()}

    for name, series_id in SGS_SERIES.items():
        rates[name] = fetch_sgs_series(series_id)
        logging.info("Série %s (%s) -> %s", name, series_id, rates[name])

    derived = compute_derived_metrics(rates)
    rates.update(derived)

    rates["fonte"] = {
        "bcb_sgs": "https://api.bcb.gov.br/dados",
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }

    write_rates(rates)
    logging.info("Arquivo de taxas atualizado em %s.", OUTPUT_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atualiza taxas do comparador.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignora a verificação do calendário do Copom.",
    )
    args = parser.parse_args()
    main(force=args.force)


