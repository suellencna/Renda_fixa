#!/usr/bin/env python3
"""
Atualiza automaticamente as taxas do comparador de renda fixa.

Busca dados de três fontes:
  1. API SGS do Banco Central — Selic meta, CDI over, IPCA 12m, IPCA mensal, TR
  2. API do Tesouro Direto — taxas dos títulos disponíveis (Prefixado, IPCA+)
  3. Métricas derivadas — CDB, LCI/LCA, Fundo DI, Poupança

Estratégia de execução:
  - Roda diariamente (via cron do Railway ou scheduler externo).
  - Compara as taxas novas com as do arquivo atual.
  - Só sobrescreve taxas.json se houve mudança real.
  - NÃO depende de datas hardcoded do Copom.

Uso:
    python scripts/update_rates.py              # atualiza se houver mudança
    python scripts/update_rates.py --force      # força gravação mesmo sem mudança
    python scripts/update_rates.py --dry-run    # mostra o que mudaria, sem gravar
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests


# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "taxas.json"
)
LOG_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "taxas.log"
)


# ---------------------------------------------------------------------------
# 1. Séries SGS do Banco Central
# ---------------------------------------------------------------------------
SGS_SERIES: Dict[str, int] = {
    "selic_meta": 432,
    "cdi_over": 4389,
    "ipca_12m": 13522,
    "ipca_mensal": 433,
    "tr_mensal": 226,
}

REQUEST_TIMEOUT = 15  # segundos


def fetch_sgs_series(series_id: int) -> Optional[float]:
    """Busca a última observação de uma série SGS do Banco Central."""
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}/"
        "dados/ultimos/1?formato=json"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        valor = data[0]["valor"].replace(",", ".")
        return round(float(valor), 4)
    except Exception as exc:
        logging.warning("Falha ao buscar série SGS %s: %s", series_id, exc)
        return None


def fetch_all_sgs() -> Dict[str, Optional[float]]:
    """Busca todas as séries SGS configuradas."""
    rates: Dict[str, Optional[float]] = {}
    for name, series_id in SGS_SERIES.items():
        value = fetch_sgs_series(series_id)
        rates[name] = value
        logging.info("SGS %s (%s) -> %s", name, series_id, value)
    return rates


# ---------------------------------------------------------------------------
# 2. API do Tesouro Direto
# ---------------------------------------------------------------------------
TESOURO_API_URL = (
    "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/"
    "service/api/treasurybondsinfo.json"
)

# Nomes parciais para identificar os títulos que nos interessam
TESOURO_TARGETS = {
    "tesouro_prefixado": "Tesouro Prefixado",       # sem juros semestrais
    "tesouro_ipca_mais": "Tesouro IPCA+",            # sem juros semestrais
    "tesouro_selic_taxa": "Tesouro Selic",
}

# Vencimentos que NÃO queremos (juros semestrais, etc.)
TESOURO_EXCLUDE_KEYWORDS = ["com Juros Semestrais"]


def fetch_tesouro_direto() -> Dict[str, Optional[float]]:
    """
    Busca taxas dos títulos do Tesouro Direto.

    Retorna a taxa do título com vencimento mais curto disponível
    para cada tipo (Prefixado, IPCA+, Selic).
    """
    result: Dict[str, Optional[float]] = {
        "tesouro_prefixado_nominal": None,
        "tesouro_ipca_mais": None,
        "tesouro_selic_taxa": None,
    }

    try:
        resp = requests.get(
            TESOURO_API_URL,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "ComparadorAtivos/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        bonds = data.get("response", {}).get("TrsrBdTradgList", [])

        if not bonds:
            logging.warning("API Tesouro Direto retornou lista vazia.")
            return result

        # Agrupa títulos por tipo
        grouped: Dict[str, list] = {
            "tesouro_prefixado": [],
            "tesouro_ipca_mais": [],
            "tesouro_selic_taxa": [],
        }

        for bond in bonds:
            info = bond.get("TrsrBd", {})
            nome = info.get("nm", "")
            taxa = info.get("anulInvstmtRate")
            venc_str = info.get("mtrtyDt", "")

            # Pula títulos com juros semestrais
            if any(kw in nome for kw in TESOURO_EXCLUDE_KEYWORDS):
                continue

            # Identifica o tipo
            for key, target_name in TESOURO_TARGETS.items():
                if target_name in nome and taxa is not None:
                    try:
                        venc_dt = datetime.strptime(
                            venc_str[:10], "%Y-%m-%d"
                        )
                        grouped[key].append({
                            "nome": nome,
                            "taxa": float(taxa),
                            "vencimento": venc_dt,
                        })
                    except (ValueError, TypeError):
                        pass

        # Para cada tipo, pega o vencimento mais curto disponível
        now = datetime.now()
        for key, bonds_list in grouped.items():
            # Filtra apenas títulos com vencimento futuro
            futuros = [b for b in bonds_list if b["vencimento"] > now]
            if not futuros:
                continue
            # Ordena por vencimento mais próximo
            futuros.sort(key=lambda b: b["vencimento"])
            chosen = futuros[0]

            if key == "tesouro_prefixado":
                result["tesouro_prefixado_nominal"] = chosen["taxa"]
            elif key == "tesouro_ipca_mais":
                result["tesouro_ipca_mais"] = chosen["taxa"]
            elif key == "tesouro_selic_taxa":
                result["tesouro_selic_taxa"] = chosen["taxa"]

            logging.info(
                "Tesouro %s -> %s%% (%s, venc %s)",
                key,
                chosen["taxa"],
                chosen["nome"],
                chosen["vencimento"].strftime("%Y-%m-%d"),
            )

    except Exception as exc:
        logging.warning("Falha ao buscar Tesouro Direto: %s", exc)

    return result


# ---------------------------------------------------------------------------
# 3. Métricas derivadas
# ---------------------------------------------------------------------------
def compute_derived_metrics(rates: Dict[str, Any]) -> Dict[str, float]:
    """Calcula métricas derivadas com base nas taxas coletadas."""
    derived: Dict[str, float] = {}
    cdi = rates.get("cdi_over")
    tr_mensal = rates.get("tr_mensal")

    if cdi is not None:
        derived["cdb_100_cdi_bruto_anual"] = round(cdi, 2)
        # IR regressivo para 12 meses (alíquota de 17.5%)
        derived["cdb_100_cdi_liquido_12m"] = round(cdi * (1 - 0.175), 2)
        # LCI/LCA 85% do CDI, isentas de IR
        derived["lci_lca_85_cdi"] = round(cdi * 0.85, 2)
        # Fundo DI com taxa de admin de 0.25% a.a.
        derived["fundo_di_liquido"] = round(max(cdi - 0.25, 0), 2)

    if tr_mensal is not None:
        # Poupança: 0.5% ao mês + TR quando Selic >= 8.5% a.a.
        poupanca_mensal = 0.5 + tr_mensal
        derived["poupanca_mensal"] = round(poupanca_mensal, 4)
        derived["poupanca_anual_aprox"] = round(
            ((1 + poupanca_mensal / 100) ** 12 - 1) * 100, 3
        )

    return derived


# ---------------------------------------------------------------------------
# 4. Comparação e gravação
# ---------------------------------------------------------------------------
COMPARE_KEYS = [
    "selic_meta", "cdi_over", "ipca_12m", "ipca_mensal", "tr_mensal",
    "tesouro_prefixado_nominal", "tesouro_ipca_mais",
]


def load_current_rates() -> Dict[str, Any]:
    """Carrega o arquivo de taxas atual, se existir."""
    if not OUTPUT_PATH.exists():
        return {}
    try:
        with OUTPUT_PATH.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def has_meaningful_change(
    old: Dict[str, Any], new: Dict[str, Any]
) -> list[str]:
    """Retorna lista de chaves que mudaram de valor."""
    changes = []
    for key in COMPARE_KEYS:
        old_val = old.get(key)
        new_val = new.get(key)
        if new_val is None:
            continue  # não sobrescreve com None
        if old_val is None or abs(float(old_val) - float(new_val)) > 0.001:
            changes.append(f"{key}: {old_val} -> {new_val}")
    return changes


def write_rates(payload: Dict[str, Any]) -> None:
    """Grava o dicionário de taxas em JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 5. Configuração de logging
# ---------------------------------------------------------------------------
def configure_logging(verbose: bool = False) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    handlers = [
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------
def main(force: bool = False, dry_run: bool = False, verbose: bool = False) -> None:
    configure_logging(verbose=verbose or dry_run)

    logging.info("=" * 60)
    logging.info(
        "Iniciando atualização (force=%s, dry_run=%s)", force, dry_run
    )

    # 1. Busca taxas do BCB
    sgs_rates = fetch_all_sgs()

    # 2. Busca taxas do Tesouro Direto
    tesouro_rates = fetch_tesouro_direto()

    # 3. Monta payload
    today = datetime.now()
    new_rates: Dict[str, Any] = {
        "data_atualizacao": today.strftime("%Y-%m-%d"),
    }

    # Adiciona séries SGS (mantém valor anterior se a API falhou)
    current = load_current_rates()
    for key in SGS_SERIES:
        new_val = sgs_rates.get(key)
        if new_val is not None:
            new_rates[key] = new_val
        elif current.get(key) is not None:
            new_rates[key] = current[key]
            logging.info("Mantendo %s anterior: %s (API falhou)", key, current[key])

    # Adiciona taxas do Tesouro (mantém anterior se a API falhou)
    for key in ["tesouro_prefixado_nominal", "tesouro_ipca_mais", "tesouro_selic_taxa"]:
        new_val = tesouro_rates.get(key)
        if new_val is not None:
            new_rates[key] = new_val
        elif current.get(key) is not None:
            new_rates[key] = current[key]
            logging.info("Mantendo %s anterior: %s (API falhou)", key, current[key])

    # 4. Métricas derivadas
    derived = compute_derived_metrics(new_rates)
    new_rates.update(derived)

    # Taxa de admin (mantém a configurada)
    new_rates["taxa_admin_fundo_di"] = current.get("taxa_admin_fundo_di", 0.25)

    # Metadados
    new_rates["fonte"] = {
        "bcb_sgs": "https://api.bcb.gov.br/dados",
        "tesouro_direto": "https://www.tesourodireto.com.br",
        "atualizado_em": today.isoformat(timespec="seconds"),
    }

    # 5. Compara com taxas atuais
    changes = has_meaningful_change(current, new_rates)

    if changes:
        logging.info("Mudanças detectadas:")
        for c in changes:
            logging.info("  %s", c)
    else:
        logging.info("Nenhuma mudança significativa detectada.")

    # 6. Grava (ou não)
    if dry_run:
        print("\n--- DRY RUN (nada gravado) ---")
        print(json.dumps(new_rates, ensure_ascii=False, indent=2))
        if changes:
            print(f"\nMudanças: {len(changes)}")
            for c in changes:
                print(f"  {c}")
        else:
            print("\nNenhuma mudança.")
        return

    if changes or force:
        write_rates(new_rates)
        logging.info("taxas.json atualizado com sucesso.")
        if not changes:
            logging.info("(Gravação forçada, sem mudanças reais.)")
    else:
        logging.info("taxas.json não alterado (sem mudanças).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Atualiza taxas do comparador de renda fixa."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Força gravação mesmo sem mudança nas taxas.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que mudaria sem gravar.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostra logs no terminal além do arquivo.",
    )
    args = parser.parse_args()
    main(force=args.force, dry_run=args.dry_run, verbose=args.verbose)
