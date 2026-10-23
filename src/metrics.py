"""Cálculos do painel, separados da interface para poderem ser testados."""
import pandas as pd

from src.config import PARIDADE_LIMITE


def media_ponderada(df, valor="preco_medio", peso="coletas", por=None):
    """Média de `valor` ponderada por `peso`, opcionalmente agrupada por `por`."""
    if df.empty:
        return pd.Series(dtype=float) if por else float("nan")
    tmp = df.assign(_vp=df[valor] * df[peso])
    if por is None:
        return tmp["_vp"].sum() / tmp[peso].sum()
    agg = tmp.groupby(por)[["_vp", peso]].sum()
    return (agg["_vp"] / agg[peso]).rename(valor)


def serie_nacional(mensal_uf, produto):
    """Preço médio mensal no Brasil (média das UFs ponderada pelo nº de coletas)."""
    df = mensal_uf[mensal_uf["produto"] == produto]
    return media_ponderada(df, por="mes").sort_index()


def deflacionar(serie, macro):
    """Converte uma série mensal nominal em reais do último mês disponível (IPCA)."""
    ipca = macro.set_index("mes")["ipca_indice"].reindex(serie.index).ffill()
    return serie * ipca.iloc[-1] / ipca


def indice_base100(serie):
    serie = serie.dropna()
    return serie / serie.iloc[0] * 100


def variacao_percentual(serie):
    """Variação do último valor em relação ao anterior, em %."""
    serie = serie.dropna()
    if len(serie) < 2:
        return None
    return (serie.iloc[-1] / serie.iloc[-2] - 1) * 100


def paridade(df, etanol="ETANOL", gasolina="GASOLINA", chaves=("uf",)):
    """Razão preço do etanol / preço da gasolina por chave, com a recomendação."""
    chaves = list(chaves)
    precos = df[df["produto"].isin([etanol, gasolina])]
    pivot = precos.pivot_table(index=chaves, columns="produto", values="preco_medio", aggfunc="mean")
    pivot = pivot.dropna(subset=[etanol, gasolina]).reset_index()
    pivot["paridade"] = pivot[etanol] / pivot[gasolina]
    pivot["compensa"] = pivot["paridade"].le(PARIDADE_LIMITE).map({True: "Etanol", False: "Gasolina"})
    return pivot.rename(columns={etanol: "preco_etanol", gasolina: "preco_gasolina"})


def correlacao_defasada(causa, efeito, max_defasagem=6):
    """Correlação entre a variação mensal de `causa` e a de `efeito` k meses depois.

    Usada para estimar com quanto atraso o petróleo chega à bomba.
    """
    base = pd.concat({"causa": causa.pct_change(), "efeito": efeito.pct_change()}, axis=1).dropna()
    linhas = [
        {"defasagem": k, "correlacao": base["causa"].corr(base["efeito"].shift(-k))}
        for k in range(max_defasagem + 1)
    ]
    return pd.DataFrame(linhas)


def regiao_mais_cara(df):
    """Região com maior preço médio, ou None quando o filtro não deixa dados."""
    if df.empty:
        return None
    return media_ponderada(df, por="regiao").idxmax()
