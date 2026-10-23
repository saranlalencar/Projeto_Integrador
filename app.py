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

NOMES_PRODUTO = {
    "GASOLINA": "gasolina comum", "GASOLINA ADITIVADA": "gasolina aditivada", "ETANOL": "etanol",
    "DIESEL": "diesel S500", "DIESEL S10": "diesel S10", "GNV": "GNV",
}

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


def pct_sinal(valor, casas=1):
    return ("+" if valor > 0 else "") + pct(valor, casas)


def num(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def rotulo_mes(mes):
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return f"{meses[mes.month - 1]}/{mes.year}"


def pergunta(titulo, contexto):
    """Abre cada aba com a pergunta que ela responde e o contexto necessário para ler os gráficos."""
    st.markdown(f"### {titulo}")
    st.markdown(contexto)


def como_ler(texto):
    st.caption(f"**Como ler:** {texto}")


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


def mostrar_ranking(tabela, rotulo, colunas_reais):
    """Tabela ordenada do mais caro ao mais barato.

    Só divide em "mais caros" e "mais baratos" quando há itens suficientes para as duas
    listas não se repetirem.
    """
    tabela = tabela.sort_values("Preço médio", ascending=False)
    exibida = tabela.copy()
    for coluna in exibida.columns:
        exibida[coluna] = exibida[coluna].map(brl if coluna in colunas_reais else lambda v: f"{v:.0f}")
    exibida.index.name = rotulo
    if len(exibida) > 10:
        caros, baratos = st.columns(2)
        caros.markdown("**5 mais caros**")
        caros.dataframe(exibida.head(5), width="stretch")
        baratos.markdown("**5 mais baratos**")
        baratos.dataframe(exibida.tail(5).iloc[::-1], width="stretch")
    else:
        st.dataframe(exibida, width="stretch")


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
    produto = st.selectbox("Produto", produtos, index=produtos.index("GASOLINA") if "GASOLINA" in produtos else 0,
                           format_func=lambda p: NOMES_PRODUTO.get(p, p).capitalize())
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
nome_produto = NOMES_PRODUTO.get(produto, produto.lower())
ultimo_mes_dados = mensal_uf["mes"].max()
janela_municipios = f"{rotulo_mes(ultimo_mes_dados - pd.DateOffset(months=5))} a {rotulo_mes(ultimo_mes_dados)}"

st.title("Preços de combustíveis no Brasil")
st.markdown(
    f"Este painel cruza **{num(mensal_uf['coletas'].sum() / 1e6, 1)} milhões de preços** coletados pela ANP em "
    f"postos de todo o país, de {rotulo_mes(meses[0])} a {rotulo_mes(meses[-1])}, com inflação, dólar e petróleo. "
    "Cada aba responde uma pergunta. Use os filtros à esquerda para olhar uma região, um estado ou outro combustível."
)
st.caption(f"Mostrando: {nome_produto} · {local} · {rotulo_mes(inicio)} a {rotulo_mes(fim)}")

if sem_dados(recorte):
    st.stop()

aba_geral, aba_causas, aba_etanol, aba_postos = st.tabs(
    ["Quanto custa", "O que move o preço", "Etanol ou gasolina?", "Bandeiras e concorrência"])

# ---------------------------------------------------------------- quanto custa
with aba_geral:
    pergunta("Quanto custa abastecer, e o preço subiu de verdade?",
             f"Os cartões mostram a média de {rotulo_mes(fim)} em {local}. A seta compara com o mês anterior: "
             "vermelho significa que ficou mais caro.")

    colunas = st.columns(4)
    for coluna, prod in zip(colunas, ["GASOLINA", "ETANOL", "DIESEL S10"]):
        serie = metrics.serie_nacional(recorte_todos_produtos, prod)
        rotulo = NOMES_PRODUTO[prod].capitalize()
        if serie.empty:
            coluna.metric(rotulo, "sem dados")
            continue
        variacao = metrics.variacao_percentual(serie)
        coluna.metric(rotulo, brl(serie.iloc[-1], 3),
                      None if variacao is None else f"{pct_sinal(variacao)} no mês", delta_color="inverse")

    par_atual = metrics.paridade(recorte_todos_produtos[recorte_todos_produtos["mes"] == fim], chaves=["mes"])
    if par_atual.empty:
        colunas[3].metric("Etanol ÷ gasolina", "sem dados")
    else:
        colunas[3].metric("Etanol ÷ gasolina", pct(par_atual["paridade"].iloc[0] * 100),
                          f"{par_atual['compensa'].iloc[0]} compensa", delta_color="off")

    st.divider()
    esquerda, direita = st.columns([3, 2], gap="large")
    with esquerda:
        nominal = metrics.serie_nacional(recorte, produto)
        real = metrics.deflacionar(nominal, macro)
        alta_nominal = (nominal.iloc[-1] / nominal.iloc[0] - 1) * 100
        alta_real = (real.iloc[-1] / real.iloc[0] - 1) * 100
        st.subheader(f"Descontada a inflação, o preço variou {pct_sinal(alta_real)} no período")
        st.markdown(f"Na bomba, o litro de {nome_produto} foi de {brl(nominal.iloc[0])} para "
                    f"{brl(nominal.iloc[-1])} ({pct_sinal(alta_nominal)}). Boa parte dessa alta só acompanhou a "
                    "inflação.")
        fig = go.Figure([
            go.Scatter(x=nominal.index, y=nominal, name="Preço na bomba", line=dict(color=AZUL, width=2.5)),
            go.Scatter(x=real.index, y=real, name=f"Corrigido pela inflação (R$ de {rotulo_mes(real.index[-1])})",
                       line=dict(color=LARANJA, width=2.5)),
        ])
        fig.update_traces(hovertemplate="R$ %{y:.2f}")
        marcar_eventos(layout(fig, yaxis_title="R$ por unidade"), inicio, fim)
        st.plotly_chart(fig, width="stretch")
        como_ler("a linha laranja mostra quanto cada preço antigo valeria hoje. Quando ela fica reta, o preço "
                 "subiu no mesmo ritmo da inflação; quando cai, o combustível ficou mais barato em termos reais.")

    with direita:
        ultimo = filtrar(mensal_uf, por_local=False)
        ultimo = ultimo[ultimo["mes"] == ultimo["mes"].max()]
        if not sem_dados(ultimo):
            por_uf = metrics.media_ponderada(ultimo, por="uf")
            st.subheader(f"Entre estados, a diferença chega a {brl(por_uf.max() - por_uf.min())}")
            st.markdown(f"Em {rotulo_mes(ultimo['mes'].max())}, o mais caro foi {ESTADOS[por_uf.idxmax()]} "
                        f"({brl(por_uf.max())}) e o mais barato, {ESTADOS[por_uf.idxmin()]} ({brl(por_uf.min())}).")
            st.plotly_chart(mapa_grade(por_uf, lambda v: num(v), "Blues", "R$"), width="stretch")
            como_ler("cada quadrado é um estado, na posição aproximada do mapa. Quanto mais escuro, mais caro.")

    st.divider()
    if uf != "Todos":
        cidades = filtrar(municipios)
        st.subheader(f"Cidades de {ESTADOS[uf]}: onde o {nome_produto} é mais caro e mais barato")
        if not sem_dados(cidades, f"A ANP não pesquisou {nome_produto} em cidades de {ESTADOS[uf]} nos últimos meses."):
            tabela = cidades.set_index("municipio")[["preco_medio", "postos"]]
            tabela.columns = ["Preço médio", "Postos pesquisados"]
            mostrar_ranking(tabela, "Cidade", ["Preço médio"])
            st.caption(f"Média de {janela_municipios}, os últimos 6 meses com dados (não segue o filtro de período).")
    else:
        por_estado = recorte.groupby("uf").apply(
            lambda g: pd.Series({"Preço médio": metrics.media_ponderada(g), "Mínimo": g["preco_min"].min(),
                                 "Máximo": g["preco_max"].max()}), include_groups=False)
        por_estado.index = por_estado.index.map(ESTADOS)
        onde = "do Brasil" if regiao == "Todas" else f"da região {REGIOES[regiao]}"
        st.subheader(f"Estados {onde} do mais caro ao mais barato no período")
        mostrar_ranking(por_estado, "Estado", ["Preço médio", "Mínimo", "Máximo"])
        st.caption("Mínimo e máximo são o menor e o maior preço encontrados em um posto no período. "
                   "Escolha um estado no filtro para ver as cidades.")

# ---------------------------------------------------------------- o que move o preço
with aba_causas:
    pergunta("O que faz o preço subir ou cair?",
             "Três suspeitos: o petróleo (cotado em dólar), o câmbio e a inflação. Como eles são nacionais, "
             f"esta aba usa sempre a média do Brasil para {nome_produto}.")

    nacional = metrics.serie_nacional(filtrar(mensal_uf, por_local=False), produto)
    macro_periodo = macro.set_index("mes").reindex(nacional.index)
    tem_brent = macro_periodo["brent_brl"].notna().sum() > 3

    series = {"Preço na bomba": (nacional, AZUL), "Inflação (IPCA)": (macro_periodo["ipca_indice"], VERDE)}
    if tem_brent:
        series["Petróleo Brent em reais"] = (macro_periodo["brent_brl"], LARANJA)
    indices = {nome: metrics.indice_base100(s) for nome, (s, _) in series.items()}
    resumo = ", ".join(f"{nome.split(' (')[0].lower()} {pct_sinal(i.iloc[-1] - 100, 0)}" for nome, i in indices.items())
    st.subheader(f"Desde {rotulo_mes(nacional.index[0])}: {resumo}")
    fig = go.Figure([go.Scatter(x=indices[nome].index, y=indices[nome], name=nome,
                                line=dict(color=cor, width=2.5), hovertemplate="%{y:.0f}")
                     for nome, (_, cor) in series.items()])
    fig.add_hline(y=100, line_color=CINZA, line_width=1)
    marcar_eventos(layout(fig, yaxis_title=f"Índice ({rotulo_mes(nacional.index[0])} = 100)"), inicio, fim)
    st.plotly_chart(fig, width="stretch")
    como_ler("todas as linhas começam em 100 para que séries com unidades diferentes (R$/litro, US$/barril, "
             "índice de preços) possam ser comparadas. Uma linha em 150 subiu 50% desde o início.")

    st.divider()
    esquerda, direita = st.columns(2, gap="large")
    with esquerda:
        if not tem_brent or len(nacional) < 12:
            st.subheader("Com quanto atraso o petróleo chega à bomba")
            st.info("É preciso ao menos 12 meses com dados do Brent para estimar o atraso. Amplie o período.")
        else:
            defasagens = metrics.correlacao_defasada(macro_periodo["brent_brl"], nacional)
            melhor = defasagens.loc[defasagens["correlacao"].idxmax()]
            k = int(melhor["defasagem"])
            st.subheader("O petróleo chega à bomba " + ("no mesmo mês" if k == 0 else f"em cerca de {k} mês" + ("es" if k > 1 else "")))
            cores = [LARANJA if d == k else AZUL for d in defasagens["defasagem"]]
            fig = go.Figure(go.Bar(x=defasagens["defasagem"], y=defasagens["correlacao"], marker_color=cores,
                                   hovertemplate="%{x} meses depois: %{y:.2f}<extra></extra>"))
            layout(fig, altura=320, xaxis_title="Meses depois da variação do petróleo",
                   yaxis_title="Correlação", hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            como_ler(f"cada barra mede o quanto uma alta (ou queda) do Brent num mês se repete na bomba alguns meses "
                     f"depois, de 0 (nenhuma relação) a 1 (sempre juntos). A barra laranja, com r = {num(melhor['correlacao'])}, "
                     "é o atraso mais comum.")

    with direita:
        disp = filtrar(mensal_uf, por_local=False).groupby("mes").apply(
            lambda g: g["preco_medio"].std() / g["preco_medio"].mean() * 100, include_groups=False)
        corte = pd.Timestamp("2023-06-01")
        antes, depois = disp[disp.index < corte], disp[disp.index >= corte]
        if len(antes) and len(depois):
            razao = depois.mean() / antes.mean()
            efeito = "reduziu" if razao < 0.95 else "aumentou" if razao > 1.05 else "não reduziu"
            st.subheader(f"O ICMS fixo por litro {efeito} a diferença entre estados")
        else:
            st.subheader("A diferença de preço entre estados ao longo do tempo")
        fig = go.Figure(go.Scatter(x=disp.index, y=disp, line=dict(color=AZUL, width=2.5),
                                   hovertemplate="%{y:.1f}%<extra></extra>"))
        marcar_eventos(layout(fig, altura=320, yaxis_title="Diferença entre estados (%)"), inicio, fim)
        st.plotly_chart(fig, width="stretch")
        texto = ("a linha mede o quanto os preços médios dos 27 estados se afastam da média nacional "
                 "(coeficiente de variação). Quanto mais alta, mais desigual o preço pelo país.")
        if len(antes) and len(depois):
            texto += (f" Antes de jun/2023, quando o ICMS virou um valor fixo por litro, a média era "
                      f"{pct(antes.mean())}; depois, {pct(depois.mean())}.")
        como_ler(texto)

# ---------------------------------------------------------------- etanol
with aba_etanol:
    pergunta("Vale mais a pena abastecer com etanol ou gasolina?",
             "Um carro flex roda cerca de 30% menos com um litro de etanol. Por isso a regra prática: **se o "
             "etanol custar até 70% do preço da gasolina, ele compensa.** Acima disso, a gasolina rende mais por "
             "real gasto.")

    base_par = filtrar(mensal_uf, por_produto=False, por_local=False)
    par_uf = metrics.paridade(base_par[base_par["mes"] == base_par["mes"].max()])
    if not sem_dados(par_uf):
        esquerda, direita = st.columns([2, 3], gap="large")
        with esquerda:
            n_etanol = int((par_uf["compensa"] == "Etanol").sum())
            st.subheader(f"O etanol compensa em {n_etanol} de {len(par_uf)} estados")
            st.markdown(f"Situação em {rotulo_mes(base_par['mes'].max())}. Os estados produtores de cana, no "
                        "Centro-Sul, têm o etanol mais barato.")
            st.plotly_chart(mapa_grade(par_uf.set_index("uf")["paridade"], lambda v: pct(v * 100, 0), "RdBu_r",
                                       "Etanol ÷<br>gasolina", faixa=(0.55, 0.85), meio=PARIDADE_LIMITE),
                            width="stretch")
            como_ler("o número é o preço do etanol como % do preço da gasolina. Azul: etanol compensa. "
                     "Vermelho: gasolina compensa. Branco: perto dos 70%, tanto faz.")
        with direita:
            par_tempo = metrics.paridade(filtrar(mensal_uf, por_produto=False), chaves=["mes", "uf"])
            par_tempo = par_tempo.groupby("mes")["paridade"].mean()
            if not sem_dados(par_tempo):
                atual = par_tempo.iloc[-1]
                lado = "abaixo" if atual <= PARIDADE_LIMITE else "acima"
                st.subheader(f"{local}: o etanol custa {pct(atual * 100, 0)} da gasolina, {lado} dos 70%")
                fig = go.Figure(go.Scatter(x=par_tempo.index, y=par_tempo * 100, line=dict(color=AZUL, width=2.5),
                                           hovertemplate="%{y:.1f}%<extra></extra>", name=local))
                fig.add_hline(y=PARIDADE_LIMITE * 100, line_dash="dash", line_color=LARANJA,
                              annotation_text="70%: abaixo da linha, etanol compensa", annotation_position="bottom left")
                st.plotly_chart(layout(fig, altura=320, yaxis_title="Etanol ÷ gasolina (%)"), width="stretch")
                como_ler("os meses em que a linha azul fica abaixo da tracejada foram os melhores para abastecer "
                         "com etanol. A entressafra da cana (dez a mar) costuma empurrar a linha para cima.")

            par_mun = metrics.paridade(filtrar(municipios, por_produto=False), chaves=["uf", "municipio"])
            par_mun = par_mun.nsmallest(10, "paridade")
            if len(par_mun):
                st.subheader(f"As 10 cidades onde o etanol mais compensa · {local}")
                exibida = pd.DataFrame({
                    "Cidade": par_mun["municipio"].str.title() + " (" + par_mun["uf"] + ")",
                    "Etanol": par_mun["preco_etanol"].map(brl),
                    "Gasolina": par_mun["preco_gasolina"].map(brl),
                    "Etanol ÷ gasolina": (par_mun["paridade"] * 100).map(lambda v: pct(v, 0)),
                })
                st.dataframe(exibida, hide_index=True, width="stretch")
                st.caption(f"Média de {janela_municipios}.")

# ---------------------------------------------------------------- bandeiras e concorrência
with aba_postos:
    pergunta("Bandeira e concorrência mudam o preço?",
             "Postos de bandeira (Ipiranga, Shell, BR) vendem a marca da distribuidora; postos de bandeira branca "
             "compram de qualquer fornecedor. A pergunta é quanto essa diferença pesa no bolso, e se cidades com "
             "mais postos têm preço menor.")

    esquerda, direita = st.columns(2, gap="large")
    with esquerda:
        band = filtrar(mensal_bandeira)
        band = band[band["mes"] > fim - pd.DateOffset(months=12)]
        band = band[band["grupo_bandeira"] != "Bandeira branca"].dropna(subset=["premio_vs_branca"])
        if sem_dados(band, "Não há postos de bandeira branca e de bandeira na mesma cidade para esses filtros."):
            pass
        else:
            premio = metrics.media_ponderada(band, valor="premio_vs_branca", por="grupo_bandeira").sort_values()
            st.subheader(f"Bandeira custa até {brl(premio.max())} a mais por litro")
            fig = go.Figure(go.Bar(x=premio, y=premio.index, orientation="h", marker_color=AZUL,
                                   text=[brl(v) for v in premio], textposition="outside",
                                   hovertemplate="%{y}: %{text}<extra></extra>"))
            layout(fig, altura=300, xaxis_title="R$ a mais por litro que a bandeira branca", hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            como_ler("cada barra compara postos da bandeira com postos de bandeira branca na mesma cidade e no "
                     "mesmo mês, nos últimos 12 meses do período. Assim a diferença não é efeito da região.")

    with direita:
        mun = filtrar(municipios)
        mun = mun[mun["postos"] >= 3]
        if sem_dados(mun if len(mun) >= 8 else None,
                     "São necessárias ao menos 8 cidades para comparar concorrência e preço. Amplie a região."):
            pass
        else:
            correl = mun["postos"].corr(mun["preco_medio"])
            if correl <= -0.3:
                titulo = "Cidades com mais postos tendem a ter preço menor"
            elif correl >= 0.3:
                titulo = "Cidades com mais postos tendem a ter preço maior"
            else:
                titulo = "Ter mais postos na cidade quase não muda o preço"
            st.subheader(titulo)
            inclinacao, intercepto = np.polyfit(np.log10(mun["postos"]), mun["preco_medio"], 1)
            xs = np.geomspace(mun["postos"].min(), mun["postos"].max(), 20)
            fig = go.Figure([
                go.Scatter(x=mun["postos"], y=mun["preco_medio"], mode="markers", name="Cidades",
                           marker=dict(color=AZUL, size=7, opacity=0.6, line=dict(color="white", width=1)),
                           text=mun["municipio"].str.title() + " (" + mun["uf"] + ")",
                           hovertemplate="%{text}<br>%{x} postos<br>R$ %{y:.2f}<extra></extra>"),
                go.Scatter(x=xs, y=intercepto + inclinacao * np.log10(xs), mode="lines", name="Tendência",
                           line=dict(color=LARANJA, dash="dash"), hoverinfo="skip"),
            ])
            fig.update_xaxes(type="log")
            layout(fig, altura=300, xaxis_title="Postos pesquisados na cidade (escala log)",
                   yaxis_title="Preço médio (R$)", hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            forca = "fraca" if abs(correl) < 0.3 else "moderada" if abs(correl) < 0.6 else "forte"
            como_ler(f"cada ponto é uma cidade ({len(mun)} no total). Se a linha laranja descesse forte, mais "
                     f"concorrência significaria preço menor. A correlação é {num(correl)} (de −1 a 1), "
                     f"uma relação {forca}. A ANP pesquisa uma amostra, não todos os postos.")
