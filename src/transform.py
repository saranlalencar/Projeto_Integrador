"""Transforma os CSVs brutos em tabelas Parquet prontas para o painel.

Lê data/raw, roda os arquivos SQL da pasta sql/ no DuckDB e grava data/processed.

Uso:
    python -m src.transform
"""
import unicodedata

import duckdb

from src.config import PROCESSED_DIR, RAW_DIR, SQL_DIR

# Nome canônico de cada coluna, a partir do nome normalizado (sem acento, minúsculo)
COLUNAS = {
    "regiao - sigla": "regiao",
    "estado - sigla": "uf",
    "municipio": "municipio",
    "revenda": "revenda",
    "cnpj da revenda": "cnpj",
    "produto": "produto",
    "data da coleta": "data_coleta",
    "valor de venda": "valor_venda",
    "unidade de medida": "unidade",
    "bandeira": "bandeira",
}

SAIDAS = {
    "mensal_uf": "02_mensal_uf.sql",
    "mensal_bandeira": "03_mensal_bandeira.sql",
    "municipio_recente": "04_municipio_recente.sql",
    "macro_mensal": "05_macro_mensal.sql",
}


def normalizar(nome):
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().replace("﻿", "").split())


def detectar_encoding(caminho):
    with open(caminho, "rb") as f:
        amostra = f.read(2_000_000)
    try:
        amostra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as erro:
        # o corte da amostra pode cair no meio de um caractere de 2 bytes
        return "utf-8" if erro.start >= len(amostra) - 3 else "latin-1"


def carregar_raw_precos(con, arquivos):
    selects = []
    for caminho in arquivos:
        leitura = (
            f"read_csv('{caminho.as_posix()}', delim=';', header=true, all_varchar=true, "
            f"encoding='{detectar_encoding(caminho)}', ignore_errors=true)"
        )
        colunas = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {leitura}").fetchall()]
        mapa = {COLUNAS[normalizar(c)]: c for c in colunas if normalizar(c) in COLUNAS}
        faltando = set(COLUNAS.values()) - set(mapa)
        if faltando:
            raise ValueError(f"{caminho.name}: colunas não encontradas {sorted(faltando)}")
        campos = ", ".join(f'"{original}" AS {canonico}' for canonico, original in mapa.items())
        selects.append(f"SELECT {campos} FROM {leitura}")
    con.execute("CREATE OR REPLACE TABLE raw_precos AS " + " UNION ALL ".join(selects))


def carregar_raw_macro(con):
    for nome in ("ipca", "dolar", "brent"):
        caminho = RAW_DIR / f"{nome}.csv"
        if caminho.exists():
            con.execute(f"CREATE OR REPLACE TABLE raw_{nome} AS SELECT * FROM read_csv('{caminho.as_posix()}')")
        else:
            con.execute(f"CREATE OR REPLACE TABLE raw_{nome} (data DATE, valor DOUBLE)")


def executar(con):
    """Roda a camada staging e as consultas finais; devolve {tabela: DataFrame}."""
    con.execute((SQL_DIR / "01_stg_precos.sql").read_text(encoding="utf-8"))
    return {nome: con.execute((SQL_DIR / arquivo).read_text(encoding="utf-8")).df()
            for nome, arquivo in SAIDAS.items()}


def main():
    arquivos = sorted(RAW_DIR.glob("anp-*.csv"))
    if not arquivos:
        raise SystemExit("Nenhum arquivo em data/raw. Rode antes: python -m src.extract")

    con = duckdb.connect()
    carregar_raw_precos(con, arquivos)
    carregar_raw_macro(con)
    tabelas = executar(con)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for nome, df in tabelas.items():
        destino = PROCESSED_DIR / f"{nome}.parquet"
        df.to_parquet(destino, index=False)
        print(f"{nome}: {len(df):,} linhas -> {destino.name}")

    total = con.execute("SELECT count(*), min(data_coleta), max(data_coleta) FROM stg_precos").fetchone()
    print(f"Coletas válidas: {total[0]:,} ({total[1]} a {total[2]})")


if __name__ == "__main__":
    main()
