import duckdb
import pytest

from src import transform

CSV = """Regiao - Sigla;Estado - Sigla;Municipio;Revenda;CNPJ da Revenda;Nome da Rua;Numero Rua;Complemento;Bairro;Cep;Produto;Data da Coleta;Valor de Venda;Valor de Compra;Unidade de Medida;Bandeira
SE;SP;CAMPINAS;POSTO A;11.111.111/0001-11;RUA X;1;;CENTRO;13000-000;GASOLINA;02/01/2024;6,00;;R$ / litro;BRANCA
SE;SP;CAMPINAS;POSTO B;22.222.222/0001-22;RUA Y;2;;CENTRO;13000-000;GASOLINA;03/01/2024;6,40;;R$ / litro;IPIRANGA
SE;SP;CAMPINAS;POSTO B;22.222.222/0001-22;RUA Y;2;;CENTRO;13000-000;ETANOL;03/01/2024;3,90;;R$ / litro;IPIRANGA
SE;SP;CAMPINAS;POSTO C;33.333.333/0001-33;RUA Z;3;;CENTRO;13000-000;GASOLINA;04/01/2024;999,00;;R$ / litro;BRANCA
SE;SP;CAMPINAS;POSTO D;44.444.444/0001-44;RUA W;4;;CENTRO;13000-000;GASOLINA;data inválida;6,10;;R$ / litro;BRANCA
"""


@pytest.fixture
def tabelas(tmp_path):
    arquivo = tmp_path / "anp-2024-01.csv"
    arquivo.write_text(CSV, encoding="latin-1")
    con = duckdb.connect()
    transform.carregar_raw_precos(con, [arquivo])
    con.execute("CREATE TABLE raw_ipca AS SELECT DATE '2024-01-01' AS data, 0.5 AS valor")
    con.execute("CREATE TABLE raw_dolar AS SELECT DATE '2024-01-01' AS data, 5.0 AS valor")
    con.execute("CREATE TABLE raw_brent AS SELECT DATE '2024-01-01' AS data, 80.0 AS valor")
    return con, transform.executar(con)


def test_remove_preco_implausivel_e_data_invalida(tabelas):
    con, _ = tabelas
    assert con.execute("SELECT count(*) FROM stg_precos").fetchone()[0] == 3


def test_cnpj_fica_so_com_digitos(tabelas):
    con, _ = tabelas
    assert con.execute("SELECT min(cnpj) FROM stg_precos").fetchone()[0] == "11111111000111"


def test_mensal_uf_agrega_por_produto(tabelas):
    _, saidas = tabelas
    gasolina = saidas["mensal_uf"].query("produto == 'GASOLINA'").iloc[0]
    assert gasolina["preco_medio"] == pytest.approx(6.20)
    assert gasolina["postos"] == 2


def test_premio_vs_branca_no_mesmo_municipio(tabelas):
    _, saidas = tabelas
    ipiranga = saidas["mensal_bandeira"].query("produto == 'GASOLINA' and grupo_bandeira == 'Ipiranga'").iloc[0]
    assert ipiranga["premio_vs_branca"] == pytest.approx(0.40)


def test_brent_convertido_para_reais(tabelas):
    _, saidas = tabelas
    assert saidas["macro_mensal"].iloc[0]["brent_brl"] == pytest.approx(400.0)


def test_normalizar_ignora_acento_e_bom():
    assert transform.normalizar("﻿Região - Sigla") == "regiao - sigla"
