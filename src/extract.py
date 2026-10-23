"""Baixa os dados brutos: série histórica de preços da ANP, IPCA, dólar e Brent.

Uso:
    python -m src.extract            # baixa tudo que ainda não existe em data/raw
    python -m src.extract --force    # baixa de novo
"""
import argparse
import io
import zipfile
from datetime import date

import pandas as pd
import requests

from src.config import (
    ANP_BASE, ANP_URLS_ESPECIAIS, BCB_SGS_URL, BRENT_URL, HEADERS,
    PRIMEIRO_SEMESTRE, RAW_DIR, SERIE_DOLAR, SERIE_IPCA,
)


def semestres(inicio=PRIMEIRO_SEMESTRE, hoje=None):
    """Lista (ano, semestre) do início até o semestre atual."""
    hoje = hoje or date.today()
    fim = (hoje.year, 1 if hoje.month <= 6 else 2)
    ano, sem = inicio
    while (ano, sem) <= fim:
        yield ano, sem
        ano, sem = (ano, 2) if sem == 1 else (ano + 1, 1)


def urls_candidatas(ano, sem):
    if (ano, sem) in ANP_URLS_ESPECIAIS:
        return [ANP_URLS_ESPECIAIS[(ano, sem)]]
    nome = f"ca-{ano}-{sem:02d}"
    return [f"{ANP_BASE}/{nome}.zip", f"{ANP_BASE}/{nome}.csv"]


def baixar_semestre(ano, sem, force=False):
    destino = RAW_DIR / f"anp-{ano}-{sem:02d}.csv"
    if destino.exists() and not force:
        return destino

    for url in urls_candidatas(ano, sem):
        resp = requests.get(url, headers=HEADERS, timeout=300)
        if resp.status_code != 200 or len(resp.content) < 1000:
            continue
        if url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                destino.write_bytes(zf.read(csvs[0]))
        else:
            destino.write_bytes(resp.content)
        print(f"ANP {ano}/{sem}: {destino.stat().st_size / 1e6:.0f} MB")
        return destino

    print(f"ANP {ano}/{sem}: ainda não publicado")
    return None


def baixar_sgs(codigo, inicio="01/01/2020"):
    url = BCB_SGS_URL.format(codigo=codigo)
    params = {"formato": "json", "dataInicial": inicio, "dataFinal": date.today().strftime("%d/%m/%Y")}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = df["valor"].astype(float)
    return df


def baixar_brent():
    resp = requests.get(BRENT_URL, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json()["value"])[["VALDATA", "VALVALOR"]]
    df.columns = ["data", "valor"]
    df["data"] = pd.to_datetime(df["data"].str[:10])
    df = df.dropna()
    return df[df["data"] >= "2020-01-01"]


def main(force=False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for ano, sem in semestres():
        baixar_semestre(ano, sem, force=force)

    baixar_sgs(SERIE_IPCA).to_csv(RAW_DIR / "ipca.csv", index=False)
    baixar_sgs(SERIE_DOLAR).to_csv(RAW_DIR / "dolar.csv", index=False)
    print("IPCA e dólar: ok")

    try:
        baixar_brent().to_csv(RAW_DIR / "brent.csv", index=False)
        print("Brent: ok")
    except requests.RequestException as erro:
        # O painel funciona sem o Brent; só a comparação com o petróleo fica de fora
        print(f"Brent: não foi possível baixar ({erro})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="baixa os arquivos de novo")
    main(force=parser.parse_args().force)
