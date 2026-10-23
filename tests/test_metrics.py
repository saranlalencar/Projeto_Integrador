import math

import pandas as pd
import pytest

from src import metrics


@pytest.fixture
def mensal():
    meses = pd.to_datetime(["2024-01-01", "2024-02-01"])
    linhas = []
    for mes, fator in zip(meses, (1.0, 1.1)):
        linhas += [
            {"mes": mes, "regiao": "SE", "uf": "SP", "produto": "GASOLINA", "preco_medio": 6.0 * fator, "coletas": 300},
            {"mes": mes, "regiao": "SE", "uf": "SP", "produto": "ETANOL", "preco_medio": 3.9 * fator, "coletas": 300},
            {"mes": mes, "regiao": "N", "uf": "AC", "produto": "GASOLINA", "preco_medio": 7.0 * fator, "coletas": 100},
            {"mes": mes, "regiao": "N", "uf": "AC", "produto": "ETANOL", "preco_medio": 5.6 * fator, "coletas": 100},
        ]
    return pd.DataFrame(linhas)


def test_media_ponderada_usa_numero_de_coletas(mensal):
    jan = mensal[(mensal["mes"] == "2024-01-01") & (mensal["produto"] == "GASOLINA")]
    # (6.0 * 300 + 7.0 * 100) / 400
    assert metrics.media_ponderada(jan) == pytest.approx(6.25)


def test_media_ponderada_vazia_retorna_nan(mensal):
    assert math.isnan(metrics.media_ponderada(mensal.iloc[0:0]))


def test_serie_nacional_ordenada_por_mes(mensal):
    serie = metrics.serie_nacional(mensal, "GASOLINA")
    assert list(serie.index) == sorted(serie.index)
    assert serie.iloc[-1] == pytest.approx(6.25 * 1.1)


def test_deflacionar_leva_valores_para_o_ultimo_mes():
    serie = pd.Series([5.0, 5.0], index=pd.to_datetime(["2024-01-01", "2024-02-01"]))
    macro = pd.DataFrame({"mes": serie.index, "ipca_indice": [1.0, 1.1]})
    real = metrics.deflacionar(serie, macro)
    assert real.iloc[0] == pytest.approx(5.5)
    assert real.iloc[-1] == pytest.approx(5.0)


def test_indice_base100_comeca_em_100():
    assert metrics.indice_base100(pd.Series([2.0, 3.0])).tolist() == [100.0, 150.0]


def test_variacao_percentual_precisa_de_dois_pontos():
    assert metrics.variacao_percentual(pd.Series([1.0])) is None
    assert metrics.variacao_percentual(pd.Series([100.0, 110.0])) == pytest.approx(10.0)


def test_paridade_recomenda_etanol_abaixo_de_70(mensal):
    par = metrics.paridade(mensal[mensal["mes"] == "2024-01-01"]).set_index("uf")
    assert par.loc["SP", "paridade"] == pytest.approx(0.65)
    assert par.loc["SP", "compensa"] == "Etanol"
    assert par.loc["AC", "compensa"] == "Gasolina"


def test_correlacao_defasada_encontra_o_atraso():
    causa = pd.Series([100, 110, 105, 120, 115, 130, 125, 140, 135, 150], dtype=float)
    efeito = causa.shift(2).bfill()
    resultado = metrics.correlacao_defasada(causa, efeito, max_defasagem=3).set_index("defasagem")
    assert resultado["correlacao"].idxmax() == 2


def test_regiao_mais_cara_trata_filtro_vazio(mensal):
    assert metrics.regiao_mais_cara(mensal.iloc[0:0]) is None
    assert metrics.regiao_mais_cara(mensal) == "N"
