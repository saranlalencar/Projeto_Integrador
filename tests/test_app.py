"""Teste de fumaça: a reportagem abre sem erro com os filtros padrão e com filtros extremos."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.config import PROCESSED_DIR, ROOT

pytestmark = pytest.mark.skipif(not (PROCESSED_DIR / "mensal_uf.parquet").exists(),
                                reason="rode python -m src.transform antes")

PRODUTO, REGIAO, ESTADO = 0, 1, 2


def abrir():
    return AppTest.from_file(ROOT / "app.py", default_timeout=120).run()


def test_reportagem_abre_sem_erro():
    app = abrir()
    assert not app.exception
    assert len(app.title) == 1
    assert len(app.metric) == 8
    capitulos = [h.value for h in app.header]
    assert len(capitulos) == 6


@pytest.mark.parametrize("produto", ["ETANOL", "DIESEL S10", "GNV"])
def test_troca_de_produto(produto):
    app = abrir()
    app.selectbox[PRODUTO].set_value(produto).run()
    assert not app.exception


def test_manchete_acompanha_o_produto():
    app = abrir()
    app.selectbox[PRODUTO].set_value("ETANOL").run()
    assert app.title[0].value.startswith("Etanol")


def test_filtro_por_estado():
    app = abrir()
    app.selectbox[REGIAO].set_value("N").run()
    app.selectbox[ESTADO].set_value("AC").run()
    assert not app.exception


def test_ranking_nao_repete_itens_quando_ha_poucos_estados():
    nacional = abrir()
    assert len(nacional.dataframe) == 3  # 5 mais caros, 5 mais baratos, cidades do etanol
    regiao = abrir()
    regiao.selectbox[REGIAO].set_value("N").run()
    assert not regiao.exception
    assert len(regiao.dataframe) == 2  # 7 estados cabem numa tabela só


def test_estado_mostra_ranking_de_cidades():
    app = abrir()
    app.selectbox[ESTADO].set_value("CE").run()
    assert not app.exception
    assert app.dataframe[0].value.index.name == "Cidade"


def test_periodo_de_um_mes_nao_quebra():
    app = abrir()
    ultimo = pd.to_datetime(pd.read_parquet(PROCESSED_DIR / "mensal_uf.parquet")["mes"]).max()
    app.select_slider[0].set_range(ultimo, ultimo).run()
    assert not app.exception
