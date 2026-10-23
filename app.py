"""Painel de preços de combustíveis no Brasil (ANP), de 2020 até hoje.

Rode com:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import metrics
from src.config import ESTADOS, PARIDADE_LIMITE, PROCESSED_DIR, REGIOES

st.set_page_config(page_title="Combustíveis no Brasil | ANP", page_icon="⛽", layout="wide")

AZUL, LARANJA, VERDE, CINZA = "#2a78d6", "#eb6834", "#1baf7a", "#76848b"
FONTE = "Fontes: ANP (Levantamento de Preços de Combustíveis), Banco Central (IPCA e dólar), Ipeadata/EIA (Brent)."

# Posição de cada UF num mapa em grade (coluna, linha), aproximando a geografia
GRADE_UF = {
    "RR": (1, 0), "AP": (3, 0), "AM": (1, 1), "PA": (2, 1), "MA": (3, 1), "CE": (4, 1), "RN": (5, 1),
    "AC": (0, 2), "RO": (1, 2), "MT": (2, 2), "TO": (3, 2), "PI": (4, 2), "PB": (5, 2),
    "MS": (2, 3), "GO": (3, 3), "DF": (4, 3), "BA": (5, 3), "PE": (6, 3),
    "SP": (3, 4), "MG": (4, 4), "SE": (5, 4), "AL": (6, 4),
    "PR": (3, 5), "RJ": (4, 5), "ES": (5, 5), "SC": (3, 6), "RS": (3, 7),
}

EVENTOS = {
    "2022-06-01": "Teto do ICMS (LC 194/2022)",
    "2023-06-01": "ICMS fixo por litro",
}


def brl(valor, casas=2):
    return f"R$ {valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor, casas=1):
    return f"{valor:.{casas}f}%".replace(".", ",")


def rotulo_mes(mes):
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return f"{meses[mes.month - 1]}/{mes.year}"


def layout(fig, altura=360, **kwargs):
    opcoes = dict(
        template="plotly_white", height=altura, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), hovermode="x unified",
        separators=",.",
    )
    fig.update_layout(**(opcoes | kwargs))
    return fig


def marcar_eventos(fig, inicio, fim):
    for data, texto in EVENTOS.items():
        data = pd.Timestamp(data)
        if inicio <= data <= fim:
            fig.add_vline(x=data, line_dash="dot", line_color=CINZA)
            fig.add_annotation(x=data, y=1, yref="paper", text=texto, showarrow=False,
                               xanchor="left", yanchor="bottom", font=dict(size=11, color=CINZA))
    return fig


def mapa_grade(valores, texto, escala, titulo_cor, faixa=None, meio=None):
    """Mapa do Brasil em grade: um quadrado por UF, sem depender de GeoJSON."""
    ufs = [uf for uf in GRADE_UF if uf in valores.index]
    x = [GRADE_UF[uf][0] for uf in ufs]
    y = [-GRADE_UF[uf][1] for uf in ufs]
    cores = valores.reindex(ufs)
    marcador = dict(symbol="square", size=46, color=cores, colorscale=escala,
                    colorbar=dict(title=titulo_cor, thickness=12), line=dict(width=0))
    if faixa:
        marcador.update(cmin=faixa[0], cmax=faixa[1])
    if meio is not None:
        marcador.update(cmid=meio)
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="markers+text", marker=marcador,
        text=[f"<b>{uf}</b><br>{texto(cores[uf])}" for uf in ufs], textfont=dict(size=10),
        hovertext=[f"{ESTADOS[uf]}: {texto(cores[uf])}" for uf in ufs], hoverinfo="text",
    ))
    fig.update_xaxes(visible=False, range=[-0.7, 6.7])
    fig.update_yaxes(visible=False, range=[-7.7, 0.7], scaleanchor="x")
    return layout(fig, altura=470, hovermode="closest")


def sem_dados(df, mensagem="Nenhum dado para os filtros escolhidos. Amplie o período ou a região."):
    if df is None or len(df) == 0:
        st.info(mensagem)
        return True
    return False


@st.cache_data
def carregar():
    tabelas = {}
    for nome in ("mensal_uf", "mensal_bandeira", "municipio_recente", "macro_mensal"):
        df = pd.read_parquet(PROCESSED_DIR / f"{nome}.parquet")
        if "mes" in df:
            df["mes"] = pd.to_datetime(df["mes"])
        tabelas[nome] = df
    return tabelas


dados = carregar()
mensal_uf, mensal_bandeira = dados["mensal_uf"], dados["mensal_bandeira"]
municipios, macro = dados["municipio_recente"], dados["macro_mensal"]

# ---------------------------------------------------------------- filtros
meses = sorted(mensal_uf["mes"].unique())
produtos = sorted(mensal_uf["produto"].unique())

with st.sidebar:
    st.header("Filtros")
    produto = st.selectbox("Produto", produtos, index=produtos.index("GASOLINA") if "GASOLINA" in produtos else 0)
    regiao = st.selectbox("Região", ["Todas"] + list(REGIOES), format_func=lambda r: REGIOES.get(r, r))
    ufs_regiao = sorted(mensal_uf.loc[mensal_uf["regiao"] == regiao, "uf"].unique()) if regiao != "Todas" \
        else sorted(mensal_uf["uf"].unique())
    uf = st.selectbox("Estado", ["Todos"] + ufs_regiao, format_func=lambda u: ESTADOS.get(u, u))
    inicio, fim = st.select_slider("Período", options=meses, value=(meses[0], meses[-1]), format_func=rotulo_mes)
    st.caption(FONTE)


def filtrar(df, por_produto=True, por_local=True):
    mascara = df["mes"].between(inicio, fim) if "mes" in df else pd.Series(True, index=df.index)
    if por_produto:
        mascara &= df["produto"] == produto
    if por_local and regiao != "Todas":
        mascara &= df["regiao"] == regiao
    if por_local and uf != "Todos":
        mascara &= df["uf"] == uf
    return df[mascara]


recorte = filtrar(mensal_uf)
recorte_todos_produtos = filtrar(mensal_uf, por_produto=False)
local = ESTADOS[uf] if uf != "Todos" else (REGIOES[regiao] if regiao != "Todas" else "Brasil")

st.title("Preços de combustíveis no Brasil")
st.caption(f"{local} · {rotulo_mes(inicio)} a {rotulo_mes(fim)} · dados semanais da ANP agregados por mês")

if sem_dados(recorte):
    st.stop()

aba_geral, aba_causas, aba_etanol, aba_postos = st.tabs(
    ["Visão geral", "O que move o preço", "Etanol × gasolina", "Postos e bandeiras"])

# ---------------------------------------------------------------- visão geral
with aba_geral:
    colunas = st.columns(4)
    for coluna, (nome, prod) in zip(colunas, [("Gasolina comum", "GASOLINA"), ("Etanol", "ETANOL"),
                                              ("Diesel S10", "DIESEL S10")]):
        serie = metrics.serie_nacional(recorte_todos_produtos, prod)
        if serie.empty:
            coluna.metric(nome, "sem dados")
            continue
        variacao = metrics.variacao_percentual(serie)
        coluna.metric(f"{nome} · {rotulo_mes(serie.index[-1])}", brl(serie.iloc[-1], 3),
                      None if variacao is None else f"{pct(variacao)} no mês", delta_color="inverse")

    par_atual = metrics.paridade(recorte_todos_produtos[recorte_todos_produtos["mes"] == fim], chaves=["mes"])
    if par_atual.empty:
        colunas[3].metric("Paridade etanol/gasolina", "sem dados")
    else:
        valor = par_atual["paridade"].iloc[0]
        colunas[3].metric("Paridade etanol/gasolina", pct(valor * 100),
                          f"{par_atual['compensa'].iloc[0]} compensa", delta_color="off")

    esquerda, direita = st.columns([3, 2])
    with esquerda:
        st.subheader("Preço nominal e preço real")
        nominal = metrics.serie_nacional(recorte, produto)
        real = metrics.deflacionar(nominal, macro)
        fig = go.Figure([
            go.Scatter(x=nominal.index, y=nominal, name="Nominal", line=dict(color=AZUL, width=2.5)),
            go.Scatter(x=real.index, y=real, name=f"Real (R$ de {rotulo_mes(real.index[-1])})",
                       line=dict(color=LARANJA, width=2.5)),
        ])
        fig.update_traces(hovertemplate="R$ %{y:.2f}")
        marcar_eventos(layout(fig, yaxis_title="R$ por unidade"), inicio, fim)
        st.plotly_chart(fig, width="stretch")
        alta_nominal = (nominal.iloc[-1] / nominal.iloc[0] - 1) * 100
        alta_real = (real.iloc[-1] / real.iloc[0] - 1) * 100
        st.caption(f"De {rotulo_mes(nominal.index[0])} a {rotulo_mes(nominal.index[-1])}, o preço nominal "
                   f"variou {pct(alta_nominal)}; descontada a inflação (IPCA), a variação foi de {pct(alta_real)}.")

    with direita:
        st.subheader(f"Preço médio por estado · {rotulo_mes(fim)}")
        ultimo = filtrar(mensal_uf, por_local=False)
        ultimo = ultimo[ultimo["mes"] == ultimo["mes"].max()]
        if not sem_dados(ultimo):
            por_uf = metrics.media_ponderada(ultimo, por="uf")
            st.plotly_chart(mapa_grade(por_uf, lambda v: f"{v:.2f}".replace(".", ","), "Blues", "R$"),
                            width="stretch")

    st.subheader("Estados mais caros e mais baratos no período")
    ranking = recorte.groupby("uf").apply(
        lambda g: pd.Series({"preco_medio": metrics.media_ponderada(g), "minimo": g["preco_min"].min(),
                             "maximo": g["preco_max"].max()}), include_groups=False)
    ranking.index = ranking.index.map(ESTADOS)
    formato = {c: st.column_config.NumberColumn(n, format="R$ %.2f")
               for c, n in [("preco_medio", "Preço médio"), ("minimo", "Mínimo"), ("maximo", "Máximo")]}
    caros, baratos = st.columns(2)
    caros.dataframe(ranking.nlargest(5, "preco_medio"), column_config=formato, width="stretch")
    baratos.dataframe(ranking.nsmallest(5, "preco_medio"), column_config=formato, width="stretch")

# ---------------------------------------------------------------- causas
with aba_causas:
    nacional = metrics.serie_nacional(filtrar(mensal_uf, por_local=False), produto)
    macro_periodo = macro.set_index("mes").reindex(nacional.index)
    tem_brent = macro_periodo["brent_brl"].notna().sum() > 3

    st.subheader("Bomba, petróleo e inflação no mesmo índice")
    series = {f"{produto.title()} na bomba": (nacional, AZUL), "IPCA": (macro_periodo["ipca_indice"], VERDE)}
    if tem_brent:
        series["Brent em reais"] = (macro_periodo["brent_brl"], LARANJA)
    fig = go.Figure([go.Scatter(x=s.dropna().index, y=metrics.indice_base100(s), name=nome,
                                line=dict(color=cor, width=2.5), hovertemplate="%{y:.0f}")
                     for nome, (s, cor) in series.items()])
    fig.add_hline(y=100, line_color=CINZA, line_width=1)
    marcar_eventos(layout(fig, yaxis_title=f"Índice ({rotulo_mes(nacional.index[0])} = 100)"), inicio, fim)
    st.plotly_chart(fig, width="stretch")
    st.caption("Índice em vez de dois eixos: todas as séries partem de 100, então a comparação é direta.")

    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Com quanto atraso o petróleo chega à bomba")
        if not tem_brent or len(nacional) < 12:
            st.info("É preciso ao menos 12 meses com dados do Brent para estimar o atraso.")
        else:
            defasagens = metrics.correlacao_defasada(macro_periodo["brent_brl"], nacional)
            melhor = defasagens.loc[defasagens["correlacao"].idxmax()]
            cores = [LARANJA if k == melhor["defasagem"] else AZUL for k in defasagens["defasagem"]]
            fig = go.Figure(go.Bar(x=defasagens["defasagem"], y=defasagens["correlacao"], marker_color=cores,
                                   hovertemplate="%{x} meses: %{y:.2f}<extra></extra>"))
            layout(fig, altura=320, xaxis_title="Defasagem (meses)", yaxis_title="Correlação", hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            st.caption(f"A variação do Brent em reais tem a maior correlação com a variação na bomba "
                       f"{int(melhor['defasagem'])} mês(es) depois (r = {melhor['correlacao']:.2f}).".replace(".", ",", 1))

    with direita:
        st.subheader("A diferença entre estados diminuiu?")
        disp = filtrar(mensal_uf, por_local=False).groupby("mes").apply(
            lambda g: g["preco_medio"].std() / g["preco_medio"].mean() * 100, include_groups=False)
        fig = go.Figure(go.Scatter(x=disp.index, y=disp, line=dict(color=AZUL, width=2.5),
                                   hovertemplate="%{y:.1f}%<extra></extra>"))
        marcar_eventos(layout(fig, altura=320, yaxis_title="Coef. de variação entre UFs (%)"), inicio, fim)
        st.plotly_chart(fig, width="stretch")
        corte = pd.Timestamp("2023-06-01")
        antes, depois = disp[disp.index < corte], disp[disp.index >= corte]
        if len(antes) and len(depois):
            st.caption(f"Dispersão média entre estados: {pct(antes.mean())} antes do ICMS fixo por litro "
                       f"e {pct(depois.mean())} depois.")

# ---------------------------------------------------------------- etanol
with aba_etanol:
    base_par = filtrar(mensal_uf, por_produto=False, por_local=False)
    par_uf = metrics.paridade(base_par[base_par["mes"] == base_par["mes"].max()])
    if not sem_dados(par_uf):
        esquerda, direita = st.columns([2, 3])
        with esquerda:
            st.subheader(f"Onde o etanol compensa · {rotulo_mes(base_par['mes'].max())}")
            st.plotly_chart(mapa_grade(par_uf.set_index("uf")["paridade"], lambda v: pct(v * 100, 0), "RdBu_r",
                                       "Etanol ÷<br>gasolina", faixa=(0.55, 0.85), meio=PARIDADE_LIMITE),
                            width="stretch")
            n_etanol = (par_uf["compensa"] == "Etanol").sum()
            st.caption(f"Abaixo de 70% (azul), o etanol rende mais por real gasto. Hoje isso vale em "
                       f"{n_etanol} de {len(par_uf)} estados.")
        with direita:
            st.subheader("Paridade ao longo do tempo")
            par_tempo = metrics.paridade(filtrar(mensal_uf, por_produto=False), chaves=["mes", "uf"])
            par_tempo = par_tempo.groupby("mes")["paridade"].mean()
            fig = go.Figure(go.Scatter(x=par_tempo.index, y=par_tempo * 100, line=dict(color=AZUL, width=2.5),
                                       hovertemplate="%{y:.1f}%<extra></extra>", name=local))
            fig.add_hline(y=PARIDADE_LIMITE * 100, line_dash="dash", line_color=LARANJA,
                          annotation_text="70%: abaixo disso, etanol compensa", annotation_position="bottom left")
            st.plotly_chart(layout(fig, altura=320, yaxis_title="Etanol ÷ gasolina (%)"), width="stretch")

            st.subheader("Cidades onde o etanol mais compensa")
            par_mun = metrics.paridade(filtrar(municipios, por_produto=False), chaves=["uf", "municipio"])
            par_mun = par_mun.nsmallest(10, "paridade")
            if not sem_dados(par_mun):
                par_mun["paridade"] *= 100
                st.dataframe(par_mun[["municipio", "uf", "preco_etanol", "preco_gasolina", "paridade"]],
                             hide_index=True, width="stretch", column_config={
                                 "municipio": "Município", "uf": "UF",
                                 "preco_etanol": st.column_config.NumberColumn("Etanol", format="R$ %.2f"),
                                 "preco_gasolina": st.column_config.NumberColumn("Gasolina", format="R$ %.2f"),
                                 "paridade": st.column_config.NumberColumn("Paridade", format="%.0f%%")})
                st.caption("Média dos últimos 6 meses de coleta.")

# ---------------------------------------------------------------- postos e bandeiras
with aba_postos:
    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Quanto se paga a mais por bandeira")
        band = filtrar(mensal_bandeira)
        band = band[band["mes"] > fim - pd.DateOffset(months=12)]
        band = band[band["grupo_bandeira"] != "Bandeira branca"].dropna(subset=["premio_vs_branca"])
        if not sem_dados(band):
            premio = metrics.media_ponderada(band, valor="premio_vs_branca", por="grupo_bandeira").sort_values()
            fig = go.Figure(go.Bar(x=premio, y=premio.index, orientation="h", marker_color=AZUL,
                                   text=[brl(v) for v in premio], textposition="outside",
                                   hovertemplate="%{y}: %{text}<extra></extra>"))
            layout(fig, altura=320, xaxis_title="Diferença para a bandeira branca no mesmo município (R$)",
                   hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            st.caption("Últimos 12 meses do período. A comparação é sempre entre postos da mesma cidade e mês.")

    with direita:
        st.subheader("Mais postos, preço menor?")
        mun = filtrar(municipios)
        mun = mun[mun["postos"] >= 3]
        if not sem_dados(mun):
            inclinacao, intercepto = np.polyfit(mun["postos"], mun["preco_medio"], 1)
            xs = np.array([mun["postos"].min(), mun["postos"].max()])
            fig = go.Figure([
                go.Scatter(x=mun["postos"], y=mun["preco_medio"], mode="markers", name="Municípios",
                           marker=dict(color=AZUL, size=7, opacity=0.6, line=dict(color="white", width=1)),
                           text=mun["municipio"] + " (" + mun["uf"] + ")",
                           hovertemplate="%{text}<br>%{x} postos<br>R$ %{y:.2f}<extra></extra>"),
                go.Scatter(x=xs, y=intercepto + inclinacao * xs, mode="lines", name="Tendência",
                           line=dict(color=LARANJA, dash="dash")),
            ])
            fig.update_xaxes(type="log")
            layout(fig, altura=320, xaxis_title="Postos pesquisados pela ANP no município (escala log)",
                   yaxis_title="Preço médio (R$)", hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            correl = mun["postos"].corr(mun["preco_medio"])
            st.caption(f"Correlação entre nº de postos e preço: {correl:.2f}. ".replace(".", ",", 1)
                       + "Substitui os antigos gráficos de dois eixos.")

    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Distribuição do preço entre municípios")
        if not sem_dados(mun):
            fig = go.Figure(go.Histogram(x=mun["preco_medio"], nbinsx=30, marker_color=AZUL,
                                         hovertemplate="R$ %{x}<br>%{y} municípios<extra></extra>"))
            st.plotly_chart(layout(fig, altura=300, xaxis_title="Preço médio (R$)", yaxis_title="Municípios",
                                   hovermode="closest", bargap=0.05), width="stretch")
    with direita:
        st.subheader("Variação de preço dentro de cada região")
        desvio = metrics.media_ponderada(recorte, valor="preco_desvio", por="regiao").rename(index=REGIOES)
        fig = go.Figure(go.Bar(x=desvio.index, y=desvio, marker_color=AZUL, text=[brl(v) for v in desvio],
                               textposition="outside", hovertemplate="%{x}: %{text}<extra></extra>"))
        st.plotly_chart(layout(fig, altura=300, yaxis_title="Desvio padrão médio (R$)", hovermode="closest"),
                        width="stretch")
