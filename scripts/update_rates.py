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
# 2. Tesouro Transparente (CSV público, atualizado diariamente)
# ---------------------------------------------------------------------------
TESOURO_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/"
    "precotaxatesourodireto.csv"
)

# Nomes parciais para identificar os títulos que nos interessam
TESOURO_TARGETS = {
    "tesouro_prefixado": "Tesouro Prefixado",       # sem juros semestrais
    "tesouro_ipca_mais": "Tesouro IPCA+",            # sem juros semestrais
    "tesouro_selic_taxa": "Tesouro Selic",
}

# Palavras que excluem títulos (juros semestrais, renda+, educa+)
TESOURO_EXCLUDE_KEYWORDS = [
    "Juros Semestrais", "Renda+", "Educa+", "RendA+",
]


def fetch_tesouro_direto() -> Dict[str, Optional[float]]:
    """
    Busca taxas dos títulos do Tesouro Direto via CSV do Tesouro
    Transparente (dados abertos, sem autenticação).

    O CSV tem ~13 MB com todo o histórico. Baixamos e filtramos
    apenas a data mais recente para extrair as taxas atuais.

    Retorna a taxa do título com vencimento mais curto disponível
    para cada tipo (Prefixado, IPCA+, Selic).
    """
    import csv
    import io

    result: Dict[str, Optional[float]] = {
        "tesouro_prefixado_nominal": None,
        "tesouro_ipca_mais": None,
        "tesouro_selic_taxa": None,
    }

    try:
        logging.info("Baixando CSV do Tesouro Transparente...")
        resp = requests.get(
            TESOURO_CSV_URL,
            timeout=60,  # CSV é grande (~13 MB)
            headers={"User-Agent": "ComparadorAtivos/1.0"},
        )
        resp.raise_for_status()

        # Detecta separador (pode ser ; ou ,)
        content = resp.content.decode("latin-1")
        reader = csv.DictReader(
            io.StringIO(content),
            delimiter=";" if ";" in content[:500] else ",",
        )

        # Mapeia colunas (nomes podem variar entre versões do CSV)
        # Colunas esperadas: Tipo Titulo, Data Venda, Data Vencimento,
        #   Taxa Compra Manha, Taxa Venda Manha, PU Compra Manha, PU Venda Manha
        rows = []
        for row in reader:
            rows.append(row)

        if not rows:
            logging.warning("CSV do Tesouro Transparente vazio.")
            return result

        # Encontra a data mais recente no CSV
        # Coluna "Data Base" ou "Data Venda" contém a data de referência
        date_col = None
        for candidate in ["Data Base", "Data Venda"]:
            if candidate in rows[0]:
                date_col = candidate
                break

        if not date_col:
            # Tenta encontrar qualquer coluna com "Data" no nome
            for col in rows[0]:
                if "Data" in col and "Vencimento" not in col:
                    date_col = col
                    break

        if not date_col:
            logging.warning("Coluna de data não encontrada no CSV.")
            return result

        # Coluna de taxa de compra
        taxa_col = None
        for candidate in ["Taxa Compra Manha", "Taxa Compra Manhã",
                          "Taxa Compra", "Taxa (% a.a.)"]:
            if candidate in rows[0]:
                taxa_col = candidate
                break

        if not taxa_col:
            for col in rows[0]:
                if "Taxa" in col and "Venda" not in col:
                    taxa_col = col
                    break

        if not taxa_col:
            logging.warning("Coluna de taxa não encontrada no CSV.")
            return result

        # Coluna do nome do título
        nome_col = None
        for candidate in ["Tipo Titulo", "Tipo Título", "Nome"]:
            if candidate in rows[0]:
                nome_col = candidate
                break

        if not nome_col:
            logging.warning("Coluna de nome do título não encontrada.")
            return result

        # Coluna de vencimento
        venc_col = None
        for candidate in ["Data Vencimento", "Vencimento"]:
            if candidate in rows[0]:
                venc_col = candidate
                break

        if not venc_col:
            logging.warning("Coluna de vencimento não encontrada.")
            return result

        logging.info(
            "CSV: %d linhas, colunas: data=%s, taxa=%s, nome=%s, venc=%s",
            len(rows), date_col, taxa_col, nome_col, venc_col,
        )

        # Pega as linhas da data mais recente
        def parse_date(s: str) -> Optional[datetime]:
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s.strip(), fmt)
                except ValueError:
                    continue
            return None

        # Encontra a data mais recente varrendo TODAS as linhas,
        # pois o CSV não é ordenado cronologicamente
        latest_date = None
        for row in rows:
            dt = parse_date(row.get(date_col, ""))
            if dt and (latest_date is None or dt > latest_date):
                latest_date = dt

        if not latest_date:
            logging.warning("Nenhuma data válida encontrada no CSV.")
            return result

        logging.info("Data mais recente no CSV: %s", latest_date.strftime("%Y-%m-%d"))

        # Filtra apenas registros da data mais recente
        latest_rows = []
        for row in rows:
            dt = parse_date(row.get(date_col, ""))
            if dt and dt == latest_date:
                latest_rows.append(row)

        # Agrupa por tipo de título
        grouped: Dict[str, list] = {
            "tesouro_prefixado": [],
            "tesouro_ipca_mais": [],
            "tesouro_selic_taxa": [],
        }

        now = datetime.now()
        for row in latest_rows:
            nome = row.get(nome_col, "")
            taxa_str = row.get(taxa_col, "").replace(",", ".").strip()
            venc_str = row.get(venc_col, "")

            if not taxa_str or not nome:
                continue

            # Pula títulos com juros semestrais e outros exclusos
            if any(kw.lower() in nome.lower() for kw in TESOURO_EXCLUDE_KEYWORDS):
                continue

            try:
                taxa = float(taxa_str)
            except ValueError:
                continue

            venc_dt = parse_date(venc_str)
            if not venc_dt or venc_dt <= now:
                continue

            # Identifica o tipo
            for key, target_name in TESOURO_TARGETS.items():
                if target_name.lower() in nome.lower():
                    grouped[key].append({
                        "nome": nome,
                        "taxa": taxa,
                        "vencimento": venc_dt,
                    })

        # Para cada tipo, pega o vencimento mais curto
        for key, bonds_list in grouped.items():
            if not bonds_list:
                continue
            bonds_list.sort(key=lambda b: b["vencimento"])
            chosen = bonds_list[0]

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
