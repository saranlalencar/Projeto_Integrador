"""Reportagem de dados: preços de combustíveis no Brasil (ANP), de 2020 até hoje.

Rode com:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import metrics
from src.config import ESTADOS, PARIDADE_LIMITE, PROCESSED_DIR, REGIOES

st.set_page_config(page_title="Combustíveis no Brasil | ANP", page_icon=":material/local_gas_station:", layout="wide")

AZUL, LARANJA, VERDE, CINZA, TINTA = "#2a78d6", "#eb6834", "#1baf7a", "#76848b", "#0f1d26"
REPOSITORIO = "https://github.com/saranlalencar/Projeto_Integrador"
FONTE = "Fontes: ANP (Levantamento de Preços de Combustíveis), Banco Central (IPCA e dólar), Ipeadata/EIA (Brent)."

NOMES_PRODUTO = {
    "GASOLINA": "gasolina comum", "GASOLINA ADITIVADA": "gasolina aditivada", "ETANOL": "etanol",
    "DIESEL": "diesel S500", "DIESEL S10": "diesel S10", "GNV": "GNV",
}

GRADE_UF = {
    "RR": (1, 0), "AP": (3, 0), "AM": (1, 1), "PA": (2, 1), "MA": (3, 1), "CE": (4, 1), "RN": (5, 1),
    "AC": (0, 2), "RO": (1, 2), "MT": (2, 2), "TO": (3, 2), "PI": (4, 2), "PB": (5, 2),
    "MS": (2, 3), "GO": (3, 3), "DF": (4, 3), "BA": (5, 3), "PE": (6, 3),
    "SP": (3, 4), "MG": (4, 4), "SE": (5, 4), "AL": (6, 4),
    "PR": (3, 5), "RJ": (4, 5), "ES": (5, 5), "SC": (3, 6), "RS": (3, 7),
}

PREPOSICAO_UF = {
    **dict.fromkeys(["AC", "AP", "AM", "CE", "DF", "ES", "MA", "MT", "MS", "PA", "PI", "PR", "RJ", "RN", "RS",
                     "TO"], "no"),
    **dict.fromkeys(["BA", "PB"], "na"),
}

EVENTOS = {
    "2022-06-01": "Teto do ICMS (LC 194/2022)",
    "2023-06-01": "ICMS fixo por litro",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
.block-container { max-width: 1120px; padding-top: 2.5rem; }
h1, h2, h3 { font-family: 'Source Serif 4', Georgia, serif !important; letter-spacing: -0.01em; }
h1 { font-size: 2.6rem !important; line-height: 1.15 !important; }
h2 { scroll-margin-top: 11rem; padding-top: 0.5rem !important; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
  font-size: 1.06rem; line-height: 1.65; max-width: 46rem; }
.chapeu { text-transform: uppercase; letter-spacing: .09em; font-size: .78rem !important;
  font-weight: 700; color: #0b6870; margin-bottom: -0.4rem !important; }
.linha-fina { font-size: 1.25rem !important; color: #41525c; line-height: 1.5 !important; }
.byline { font-size: .88rem !important; color: #5c6b73; border-top: 1px solid #dfe5e8;
  border-bottom: 1px solid #dfe5e8; padding: .55rem 0; }
.destaque { border-top: 3px solid #0f1d26; padding-top: .6rem; margin-bottom: 1rem; }
.destaque .valor { display: block; font-family: 'Source Serif 4', Georgia, serif; font-size: 2.6rem;
  font-weight: 700; line-height: 1.1; color: #0f1d26; }
.destaque .legenda { display: block; font-size: .95rem; color: #41525c; margin-top: .25rem; }
[data-testid="stLayoutWrapper"]:has(> .st-key-filtros) { position: sticky; top: 3.75rem; z-index: 990;
  background: #ffffff; border-bottom: 1px solid #dfe5e8; padding: .4rem 0 .2rem; }
.st-key-resumo { background: #f3f6f7; border-left: 4px solid #0b6870; border-radius: 4px;
  padding: 1rem 1.3rem; }
[class*="st-key-bolso"] { background: #fff7f1; border-left: 4px solid #eb6834 !important; }
[class*="st-key-entenda"] { background: #f3f6f7; border-left: 4px solid #2a78d6 !important; }
.indice a { color: #0b6870 !important; text-decoration: none; font-weight: 600; }
.fim { border-top: 1px solid #dfe5e8; padding-top: 1rem; }
</style>
"""


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


def md(texto_):
    # "R$ ... R$" seria lido como fórmula LaTeX pelo Markdown do Streamlit
    return texto_.replace("$", r"\$")


def texto(conteudo):
    st.markdown(md(conteudo))


def html(conteudo):
    st.markdown(conteudo, unsafe_allow_html=True)


def secao(numero, ancora, chapeu, titulo):
    html(f'<p class="chapeu">{f"{numero} · " if numero else ""}{chapeu}</p>')
    st.header(md(titulo), anchor=ancora)


def destaque(valor, legenda):
    html(f'<div class="destaque"><span class="valor">{valor}</span><span class="legenda">{legenda}</span></div>')


def quadro(tipo, chave, titulo, conteudo):
    with st.container(border=True, key=f"{tipo}_{chave}"):
        texto(f"**{titulo}**  \n{conteudo}")


def como_ler(conteudo):
    st.caption(md(f"**Como ler:** {conteudo}"))


def layout(fig, altura=360, **kwargs):
    opcoes = dict(
        template="plotly_white", height=altura, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0), hovermode="x unified",
        separators=",.", font=dict(color=TINTA), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(**(opcoes | kwargs))
    return fig


def marcar_eventos(fig, inicio, fim):
    visiveis = [(pd.Timestamp(d), r) for d, r in EVENTOS.items() if inicio <= pd.Timestamp(d) <= fim]
    for i, (data, rotulo) in enumerate(visiveis):
        fig.add_vline(x=data, line_dash="dot", line_color=CINZA)
        # alterna a altura das etiquetas para eventos próximos não se sobreporem
        fig.add_annotation(x=data, y=0.99 - 0.08 * (i % 2), yref="paper", text=f" {rotulo}", showarrow=False,
                           xanchor="left", yanchor="top", bgcolor="rgba(255,255,255,0.85)",
                           font=dict(size=11, color=CINZA))
    return fig


def mapa_grade(valores, rotulo, escala, titulo_cor, faixa=None, meio=None):
    """Mapa do Brasil em grade: um quadrado por UF, sem depender de GeoJSON."""
    ufs = [uf for uf in GRADE_UF if uf in valores.index]
    cores = valores.reindex(ufs)
    marcador = dict(symbol="square", size=46, color=cores, colorscale=escala,
                    colorbar=dict(title=titulo_cor, thickness=12), line=dict(width=0))
    if faixa:
        marcador.update(cmin=faixa[0], cmax=faixa[1])
    if meio is not None:
        marcador.update(cmid=meio)
    fig = go.Figure(go.Scatter(
        x=[GRADE_UF[uf][0] for uf in ufs], y=[-GRADE_UF[uf][1] for uf in ufs], mode="markers+text",
        marker=marcador, text=[f"<b>{uf}</b><br>{rotulo(cores[uf])}" for uf in ufs], textfont=dict(size=10),
        hovertext=[f"{ESTADOS[uf]}: {rotulo(cores[uf])}" for uf in ufs], hoverinfo="text",
    ))
    fig.update_xaxes(visible=False, range=[-0.7, 6.7])
    fig.update_yaxes(visible=False, range=[-7.7, 0.7], scaleanchor="x")
    return layout(fig, altura=470, hovermode="closest")


def mostrar_ranking(tabela, rotulo, colunas_reais):
    """Tabela do mais caro ao mais barato; só divide em duas listas quando elas não se repetem."""
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


def aviso(mensagem):
    st.info(mensagem)


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
meses = sorted(mensal_uf["mes"].unique())
produtos = sorted(mensal_uf["produto"].unique())
ultimo_mes_dados = mensal_uf["mes"].max()
janela_municipios = f"{rotulo_mes(ultimo_mes_dados - pd.DateOffset(months=5))} a {rotulo_mes(ultimo_mes_dados)}"

html(CSS)
cabecalho = st.container()

# ---------------------------------------------------------------- filtros (barra fixa)
with st.container(key="filtros"):
    c_prod, c_reg, c_uf, c_per = st.columns([1.1, 1, 1.2, 2.2])
    produto = c_prod.selectbox("Combustível", produtos,
                               index=produtos.index("GASOLINA") if "GASOLINA" in produtos else 0,
                               format_func=lambda p: NOMES_PRODUTO.get(p, p).capitalize())
    regiao = c_reg.selectbox("Região", ["Todas"] + list(REGIOES), format_func=lambda r: REGIOES.get(r, r))
    ufs_regiao = sorted(mensal_uf.loc[mensal_uf["regiao"] == regiao, "uf"].unique()) if regiao != "Todas" \
        else sorted(mensal_uf["uf"].unique())
    uf = c_uf.selectbox("Estado", ["Todos"] + ufs_regiao, format_func=lambda u: ESTADOS.get(u, u))
    inicio, fim = c_per.select_slider("Período", options=meses, value=(meses[0], meses[-1]),
                                      format_func=rotulo_mes)


def filtrar(df, por_produto=True, por_local=True):
    mascara = df["mes"].between(inicio, fim) if "mes" in df else pd.Series(True, index=df.index)
    if por_produto:
        mascara &= df["produto"] == produto
    if por_local and regiao != "Todas":
        mascara &= df["regiao"] == regiao
    if por_local and uf != "Todos":
        mascara &= df["uf"] == uf
    return df[mascara]


local = ESTADOS[uf] if uf != "Todos" else (REGIOES[regiao] if regiao != "Todas" else "Brasil")
if uf != "Todos":
    em_local = f"{PREPOSICAO_UF.get(uf, 'em')} {local}"
else:
    em_local = f"na região {local}" if regiao != "Todas" else "no Brasil"
nome_produto = NOMES_PRODUTO.get(produto, produto.lower())
unidade, sigla, tanque = ("m³", "m³", 15) if produto == "GNV" else ("litro", "litros", 50)

recorte = filtrar(mensal_uf)
if recorte.empty:
    with cabecalho:
        st.title("Preços de combustíveis no Brasil")
    aviso("Nenhum dado para os filtros escolhidos. Amplie o período ou a região.")
    st.stop()

# ---------------------------------------------------------------- apuração: todos os números da página
recorte_todos = filtrar(mensal_uf, por_produto=False)
brasil_produto = filtrar(mensal_uf, por_local=False)

nominal = metrics.serie_nacional(recorte, produto)
real = metrics.deflacionar(nominal, macro)
um_mes = len(nominal) < 2
alta_nominal = (nominal.iloc[-1] / nominal.iloc[0] - 1) * 100
alta_real = (real.iloc[-1] / real.iloc[0] - 1) * 100
ipca = macro.set_index("mes")["ipca_indice"].reindex(nominal.index).ffill()
ipca_acumulado = (ipca.iloc[-1] / ipca.iloc[0] - 1) * 100

mes_mapa = brasil_produto["mes"].max()
por_uf = metrics.media_ponderada(brasil_produto[brasil_produto["mes"] == mes_mapa], por="uf").sort_values()
diferenca_uf = por_uf.max() - por_uf.min()

nacional = metrics.serie_nacional(brasil_produto, produto)
macro_periodo = macro.set_index("mes").reindex(nacional.index)
tem_brent = macro_periodo["brent_brl"].notna().sum() > 3
defasagens = melhor = None
if tem_brent and len(nacional) >= 12:
    defasagens = metrics.correlacao_defasada(macro_periodo["brent_brl"], nacional)
    melhor = defasagens.loc[defasagens["correlacao"].idxmax()]
atraso = None if melhor is None else int(melhor["defasagem"])

base_par = filtrar(mensal_uf, por_produto=False, por_local=False)
mes_par = base_par["mes"].max()
par_uf = metrics.paridade(base_par[base_par["mes"] == mes_par])
n_etanol = int((par_uf["compensa"] == "Etanol").sum())
par_tempo = metrics.paridade(recorte_todos, chaves=["mes", "uf"]).groupby("mes")["paridade"].mean()

band = filtrar(mensal_bandeira)
band = band[band["mes"] > fim - pd.DateOffset(months=12)]
band = band[band["grupo_bandeira"] != "Bandeira branca"].dropna(subset=["premio_vs_branca"])
premio = metrics.media_ponderada(band, valor="premio_vs_branca", por="grupo_bandeira").sort_values() \
    if len(band) else pd.Series(dtype=float)

mun = filtrar(municipios)
mun = mun[mun["postos"] >= 3]
correl = mun["postos"].corr(mun["preco_medio"]) if len(mun) >= 8 else None


def manchete():
    nome = nome_produto.capitalize()
    if um_mes:
        return f"{nome}: quanto custa abastecer em {rotulo_mes(fim)}"
    movimento = f"{'alta' if alta_nominal >= 0 else 'queda'} de {pct(abs(alta_nominal), 0)} na bomba desde {rotulo_mes(nominal.index[0])}"
    if abs(alta_real) < 3:
        return f"{nome}: {movimento}, mas quase toda ela é inflação"
    if alta_real > 0:
        return f"{nome}: {movimento}, {pct(alta_real, 0)} acima da inflação"
    return f"{nome}: {movimento}, mas o preço real caiu {pct(-alta_real, 0)}"


# ---------------------------------------------------------------- cabeçalho
with cabecalho:
    html('<p class="chapeu">Reportagem de dados · Combustíveis</p>')
    st.title(md(manchete()), anchor=False)
    html(f'<p class="linha-fina">{num(mensal_uf["coletas"].sum() / 1e6, 1)} milhões de preços coletados pela ANP '
         'em postos de todo o país mostram quanto o combustível subiu de verdade, onde abastecer custa mais, '
         'o que move o preço e quando o etanol compensa.</p>')
    html(f'<p class="byline">Por <b>Sara Alencar</b> · Dados até {rotulo_mes(ultimo_mes_dados)} · '
         'Leitura de 6 minutos · Os textos se reescrevem conforme os filtros abaixo</p>')

st.caption(md(f"Mostrando **{nome_produto}** {em_local}, de {rotulo_mes(inicio)} a {rotulo_mes(fim)}."))

# ---------------------------------------------------------------- em 30 segundos
with st.container(key="resumo"):
    pontos = []
    if not um_mes:
        pontos.append(f"**Preço real:** descontada a inflação de {pct(ipca_acumulado, 0)}, o {unidade} de "
                      f"{nome_produto} variou {pct_sinal(alta_real)} {em_local}.")
    pontos.append(f"**Geografia:** em {rotulo_mes(mes_mapa)}, {ESTADOS[por_uf.idxmax()]} pagou "
                  f"{brl(diferenca_uf)} a mais por {unidade} que {ESTADOS[por_uf.idxmin()]}.")
    if atraso is not None:
        pontos.append("**Petróleo:** uma alta do Brent chega à bomba "
                      + ("no mesmo mês." if atraso == 0 else f"em cerca de {atraso} mês" + ("es." if atraso > 1 else ".")))
    if len(par_uf):
        pontos.append(f"**Etanol:** compensa em {n_etanol} de {len(par_uf)} estados ({rotulo_mes(mes_par)}).")
    if len(premio):
        pontos.append(f"**Bandeira:** {premio.idxmax()} cobra até {brl(premio.max())} a mais por {unidade} "
                      "que a bandeira branca da mesma cidade.")
    texto("**Em 30 segundos**\n\n" + "\n".join(f"- {p}" for p in pontos))

html('<p class="indice"><b>Nesta reportagem:</b> '
     '<a href="#painel">Painel do mês</a> · <a href="#preco-real">1. Subiu de verdade?</a> · '
     '<a href="#onde">2. Onde é mais caro</a> · <a href="#causas">3. O que move o preço</a> · '
     '<a href="#etanol">4. Etanol ou gasolina</a> · <a href="#bandeiras">5. Bandeiras</a> · '
     '<a href="#metodo">Como foi feito</a></p>')

# ---------------------------------------------------------------- painel do mês
st.subheader(md(f"Painel de {rotulo_mes(fim)} · {local}"), anchor="painel")
cartoes = st.columns(4)
for coluna, prod in zip(cartoes, ["GASOLINA", "ETANOL", "DIESEL S10"]):
    serie = metrics.serie_nacional(recorte_todos, prod)
    rotulo = NOMES_PRODUTO[prod].capitalize()
    if serie.empty:
        coluna.metric(rotulo, "sem dados", border=True)
        continue
    variacao = metrics.variacao_percentual(serie)
    coluna.metric(rotulo, brl(serie.iloc[-1], 3), None if variacao is None else f"{pct_sinal(variacao)} no mês",
                  delta_color="inverse", chart_data=serie.tail(12).round(3).tolist(), chart_type="line",
                  border=True, help="Preço médio no último mês do período. O minigráfico mostra os últimos 12 meses.")
if par_tempo.empty:
    cartoes[3].metric("Etanol ÷ gasolina", "sem dados", border=True)
else:
    atual = par_tempo.iloc[-1]
    cartoes[3].metric("Etanol ÷ gasolina", pct(atual * 100), f"{'etanol' if atual <= PARIDADE_LIMITE else 'gasolina'} compensa",
                      delta_color="off", chart_data=(par_tempo.tail(12) * 100).round(1).tolist(), chart_type="line",
                      border=True, help="Abaixo de 70%, o etanol rende mais por real gasto.")

ultimo_recorte = recorte[recorte["mes"] == recorte["mes"].max()]
extras = st.columns(4)
extras[0].metric("Postos no mês", f"{int(ultimo_recorte['postos'].sum()):,}".replace(",", "."), border=True,
                 help="Postos visitados pela ANP no último mês do período.")
extras[1].metric("Preços coletados", f"{int(recorte['coletas'].sum()):,}".replace(",", "."), border=True,
                 help="Total de preços coletados no período e local escolhidos.")
extras[2].metric("Menor preço num posto", brl(recorte["preco_min"].min()), border=True,
                 help="Menor preço encontrado em um único posto no período.")
extras[3].metric("Maior preço num posto", brl(recorte["preco_max"].max()), border=True,
                 help="Maior preço encontrado em um único posto no período.")

# ---------------------------------------------------------------- 1. preço real
st.divider()
if um_mes:
    secao(1, "preco-real", "Preço real", "Escolha um período maior para ver se o preço subiu de verdade")
    aviso("Com um único mês não há variação para comparar com a inflação.")
else:
    titulo = (f"Descontada a inflação, o preço variou só {pct_sinal(alta_real)}" if abs(alta_real) < 3
              else f"Descontada a inflação, o preço variou {pct_sinal(alta_real)}")
    secao(1, "preco-real", "Preço real", titulo)
    texto(f"Na bomba, o {unidade} de {nome_produto} {em_local} foi de {brl(nominal.iloc[0])} em "
          f"{rotulo_mes(nominal.index[0])} para {brl(nominal.iloc[-1])} em {rotulo_mes(nominal.index[-1])}, "
          f"uma variação de {pct_sinal(alta_nominal)}. Parece muito, mas quase tudo ficou mais caro no período: "
          f"a inflação oficial (IPCA) acumulou {pct(ipca_acumulado)}. Para saber se o combustível passou a pesar "
          "mais no orçamento, é preciso comparar as duas coisas.")
    grafico, lateral = st.columns([3, 1.3], gap="large")
    with grafico:
        fig = go.Figure([
            go.Scatter(x=nominal.index, y=nominal, name="Preço na bomba", line=dict(color=AZUL, width=2.5)),
            go.Scatter(x=real.index, y=real, name=f"Corrigido pela inflação (R$ de {rotulo_mes(real.index[-1])})",
                       line=dict(color=LARANJA, width=2.5)),
        ])
        fig.update_traces(hovertemplate="R$ %{y:.2f}")
        marcar_eventos(layout(fig, yaxis_title=f"R$ por {unidade}"), inicio, fim)
        st.plotly_chart(fig, width="stretch")
        como_ler("a linha laranja mostra quanto cada preço antigo valeria hoje. Quando ela fica reta, o preço "
                 "subiu no mesmo ritmo da inflação; quando cai, o combustível ficou mais barato em termos reais.")
    with lateral:
        destaque(pct_sinal(alta_real), "variação do preço descontada a inflação")
        destaque(pct_sinal(alta_nominal), "variação na bomba, sem descontar a inflação")
    quadro("bolso", "real", "No seu bolso",
           f"Encher um tanque de {tanque} {sigla} custava {brl(tanque * nominal.iloc[0])} em "
           f"{rotulo_mes(nominal.index[0])} e custa {brl(tanque * nominal.iloc[-1])} agora. Corrigido pela "
           f"inflação, aquele tanque antigo sairia {brl(tanque * real.iloc[0])} em dinheiro de hoje.")

# ---------------------------------------------------------------- 2. onde é mais caro
st.divider()
secao(2, "onde", "Geografia", f"Entre estados, a diferença chega a {brl(diferenca_uf)} por {unidade}")
texto(f"Em {rotulo_mes(mes_mapa)}, o {unidade} de {nome_produto} mais caro estava em {ESTADOS[por_uf.idxmax()]} "
      f"({brl(por_uf.max())}) e o mais barato, em {ESTADOS[por_uf.idxmin()]} ({brl(por_uf.min())}). "
      "Costumam pesar na conta a distância até as refinarias e portos, o custo do frete e a margem de "
      "distribuidoras e postos, que variam muito de um mercado para outro.")
mapa, lateral = st.columns([3, 2], gap="large")
with mapa:
    st.plotly_chart(mapa_grade(por_uf, lambda v: num(v), "Blues", "R$"), width="stretch")
    como_ler("cada quadrado é um estado, na posição aproximada do mapa. Quanto mais escuro, mais caro. "
             "O mapa mostra sempre o país inteiro, para servir de referência.")
with lateral:
    destaque(brl(tanque * diferenca_uf), f"a mais num tanque de {tanque} {sigla} em {ESTADOS[por_uf.idxmax()]} "
                                         f"do que em {ESTADOS[por_uf.idxmin()]}")
    if uf != "Todos" and uf in por_uf.index:
        posicao = int(por_uf.rank(ascending=False)[uf])
        destaque(f"{posicao}º", f"posição de {ESTADOS[uf]} entre os {len(por_uf)} estados, do mais caro ao mais barato")

if uf != "Todos":
    cidades = filtrar(municipios)
    st.subheader(md(f"Cidades de {ESTADOS[uf]}: onde o {nome_produto} é mais caro e mais barato"), anchor=False)
    if cidades.empty:
        aviso(f"A ANP não pesquisou {nome_produto} em cidades de {ESTADOS[uf]} nos últimos meses.")
    else:
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
    st.subheader(f"Estados {onde}, do mais caro ao mais barato no período", anchor=False)
    mostrar_ranking(por_estado, "Estado", ["Preço médio", "Mínimo", "Máximo"])
    st.caption("Mínimo e máximo são o menor e o maior preço encontrados em um posto no período. "
               "Escolha um estado no filtro para ver as cidades.")

# ---------------------------------------------------------------- 3. o que move o preço
st.divider()
series = {"Preço na bomba": (nacional, AZUL), "Inflação (IPCA)": (macro_periodo["ipca_indice"], VERDE)}
if tem_brent:
    series["Petróleo Brent em reais"] = (macro_periodo["brent_brl"], LARANJA)
indices = {nome: metrics.indice_base100(s) for nome, (s, _) in series.items()}
resumo = ", ".join(f"{nome.split(' (')[0].lower()} {pct_sinal(i.iloc[-1] - 100, 0)}" for nome, i in indices.items())
secao(3, "causas", "O que move o preço", f"Desde {rotulo_mes(nacional.index[0])}: {resumo}")
texto(f"Três fatores aparecem sempre que se fala em preço de combustível: o petróleo, cotado em dólar no "
      f"mercado internacional, o câmbio e a inflação. Como eles valem para o país todo, este capítulo usa a "
      f"média do Brasil para {nome_produto}, mesmo com um estado selecionado.")
fig = go.Figure([go.Scatter(x=indices[nome].index, y=indices[nome], name=nome,
                            line=dict(color=cor, width=2.5), hovertemplate="%{y:.0f}")
                 for nome, (_, cor) in series.items()])
fig.add_hline(y=100, line_color=CINZA, line_width=1)
marcar_eventos(layout(fig, yaxis_title=f"Índice ({rotulo_mes(nacional.index[0])} = 100)"), inicio, fim)
st.plotly_chart(fig, width="stretch")
como_ler("todas as linhas começam em 100 para que séries com unidades diferentes (R$ por litro, US$ por "
         "barril, índice de preços) possam ser comparadas. Uma linha em 150 subiu 50% desde o início.")

esquerda, direita = st.columns(2, gap="large")
with esquerda:
    if defasagens is None:
        st.subheader("Com quanto atraso o petróleo chega à bomba", anchor=False)
        aviso("É preciso ao menos 12 meses com dados do Brent para estimar o atraso. Amplie o período.")
    else:
        st.subheader("O petróleo chega à bomba " + ("no mesmo mês" if atraso == 0 else
                     f"em cerca de {atraso} mês" + ("es" if atraso > 1 else "")), anchor=False)
        cores = [LARANJA if d == atraso else AZUL for d in defasagens["defasagem"]]
        fig = go.Figure(go.Bar(x=defasagens["defasagem"], y=defasagens["correlacao"], marker_color=cores,
                               hovertemplate="%{x} meses depois: %{y:.2f}<extra></extra>"))
        layout(fig, altura=300, xaxis_title="Meses depois da variação do petróleo",
               yaxis_title="Correlação", hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        como_ler(f"cada barra mede o quanto uma alta (ou queda) do Brent num mês se repete na bomba alguns meses "
                 f"depois, de 0 (nenhuma relação) a 1 (sempre juntos). A barra laranja, com r = "
                 f"{num(melhor['correlacao'])}, é o atraso mais comum.")
        quadro("entenda", "atraso", "Por que existe atraso?",
               "Refinarias e importadores reajustam o preço de tempos em tempos, e distribuidoras e postos "
               "ainda vendem o combustível que compraram antes. Por isso a alta do petróleo leva semanas para "
               "aparecer na bomba, e a queda também.")

with direita:
    disp = brasil_produto.groupby("mes").apply(
        lambda g: g["preco_medio"].std() / g["preco_medio"].mean() * 100, include_groups=False)
    corte = pd.Timestamp("2023-06-01")
    antes, depois = disp[disp.index < corte], disp[disp.index >= corte]
    if len(antes) and len(depois):
        razao = depois.mean() / antes.mean()
        efeito = "reduziu" if razao < 0.95 else "aumentou" if razao > 1.05 else "não reduziu"
        st.subheader(f"O ICMS fixo por litro {efeito} a diferença entre estados", anchor=False)
    else:
        st.subheader("A diferença de preço entre estados ao longo do tempo", anchor=False)
    fig = go.Figure(go.Scatter(x=disp.index, y=disp, line=dict(color=AZUL, width=2.5),
                               hovertemplate="%{y:.1f}%<extra></extra>"))
    marcar_eventos(layout(fig, altura=300, yaxis_title="Diferença entre estados (%)"), inicio, fim)
    st.plotly_chart(fig, width="stretch")
    explicacao = ("a linha mede o quanto os preços médios dos 27 estados se afastam da média nacional "
                  "(coeficiente de variação). Quanto mais alta, mais desigual o preço pelo país.")
    if len(antes) and len(depois):
        explicacao += f" Antes de jun/2023 a média era {pct(antes.mean())}; depois, {pct(depois.mean())}."
    como_ler(explicacao)
    quadro("entenda", "icms", "O que mudou no ICMS",
           "Em jun/2022, a Lei Complementar 194 limitou o ICMS sobre combustíveis. Em 2023, o imposto deixou "
           "de ser uma porcentagem do preço, diferente em cada estado, e virou um valor fixo por litro, "
           "igual em todo o país (na gasolina, desde jun/2023).")

# ---------------------------------------------------------------- 4. etanol ou gasolina
st.divider()
titulo = f"O etanol compensa em {n_etanol} de {len(par_uf)} estados" if len(par_uf) else "Etanol ou gasolina?"
secao(4, "etanol", "Etanol ou gasolina", titulo)
texto("Um carro flex roda cerca de 30% menos com um litro de etanol do que com um de gasolina. Daí vem a regra "
      "prática: **se o etanol custar até 70% do preço da gasolina, ele compensa.** Acima disso, a gasolina rende "
      f"mais por real gasto. Os estados produtores de cana, no Centro-Sul, costumam ter o etanol mais barato.")
if par_uf.empty:
    aviso("Não há preços de etanol e gasolina no mesmo mês para esses filtros.")
else:
    esquerda, direita = st.columns([2, 3], gap="large")
    with esquerda:
        st.plotly_chart(mapa_grade(par_uf.set_index("uf")["paridade"], lambda v: pct(v * 100, 0), "RdBu_r",
                                   "Etanol ÷<br>gasolina", faixa=(0.55, 0.85), meio=PARIDADE_LIMITE),
                        width="stretch")
        como_ler(f"situação em {rotulo_mes(mes_par)}. O número é o preço do etanol como % do preço da gasolina. "
                 "Azul: etanol compensa. Vermelho: gasolina compensa. Branco: perto dos 70%, tanto faz.")
    with direita:
        if not par_tempo.empty:
            atual = par_tempo.iloc[-1]
            lado = "abaixo" if atual <= PARIDADE_LIMITE else "acima"
            st.subheader(md(f"{local}: o etanol custa {pct(atual * 100, 0)} da gasolina, {lado} dos 70%"), anchor=False)
            fig = go.Figure(go.Scatter(x=par_tempo.index, y=par_tempo * 100, line=dict(color=AZUL, width=2.5),
                                       hovertemplate="%{y:.1f}%<extra></extra>", name=local))
            fig.add_hline(y=PARIDADE_LIMITE * 100, line_dash="dash", line_color=LARANJA,
                          annotation_text="70%: abaixo da linha, etanol compensa", annotation_position="bottom left")
            st.plotly_chart(layout(fig, altura=300, yaxis_title="Etanol ÷ gasolina (%)"), width="stretch")
            como_ler("os meses em que a linha azul fica abaixo da tracejada foram os melhores para abastecer "
                     "com etanol. A entressafra da cana (dez a mar) costuma empurrar a linha para cima.")

    preco_g = metrics.serie_nacional(recorte_todos, "GASOLINA")
    preco_e = metrics.serie_nacional(recorte_todos, "ETANOL")
    if len(preco_g) and len(preco_e):
        custo_g = 1000 / 12 * preco_g.iloc[-1]
        custo_e = 1000 / (12 * 0.7) * preco_e.iloc[-1]
        melhor_comb = "o etanol" if custo_e < custo_g else "a gasolina"
        quadro("bolso", "etanol", "No seu bolso",
               f"Um carro flex que faz 12 km/l com gasolina faz cerca de 8,4 km/l com etanol. Com os preços de "
               f"{rotulo_mes(preco_g.index[-1])} {em_local}, rodar 1.000 km custa {brl(custo_g)} com gasolina e "
               f"{brl(custo_e)} com etanol: {melhor_comb} sai {brl(abs(custo_g - custo_e))} mais barato.")

    par_mun = metrics.paridade(filtrar(municipios, por_produto=False), chaves=["uf", "municipio"]).nsmallest(10, "paridade")
    if len(par_mun):
        st.subheader(md(f"As 10 cidades onde o etanol mais compensa · {local}"), anchor=False)
        st.dataframe(pd.DataFrame({
            "Cidade": par_mun["municipio"].str.title() + " (" + par_mun["uf"] + ")",
            "Etanol": par_mun["preco_etanol"].map(brl),
            "Gasolina": par_mun["preco_gasolina"].map(brl),
            "Etanol ÷ gasolina": (par_mun["paridade"] * 100).map(lambda v: pct(v, 0)),
        }), hide_index=True, width="stretch")
        st.caption(f"Média de {janela_municipios}.")

# ---------------------------------------------------------------- 5. bandeiras e concorrência
st.divider()
titulo = f"Abastecer em posto de bandeira custa até {brl(premio.max())} a mais por {unidade}" if len(premio) \
    else "Bandeira e concorrência mudam o preço?"
secao(5, "bandeiras", "Bandeiras e concorrência", titulo)
texto("Postos de bandeira (Ipiranga, Shell, BR) vendem a marca de uma distribuidora; postos de bandeira branca "
      "compram de qualquer fornecedor. A comparação abaixo é feita entre postos da mesma cidade e do mesmo mês, "
      "para que a diferença não seja apenas efeito da região. Também testamos se cidades com mais postos, e "
      "portanto mais concorrência, têm preço menor.")
esquerda, direita = st.columns(2, gap="large")
with esquerda:
    if premio.empty:
        aviso("Não há postos de bandeira branca e de bandeira na mesma cidade para esses filtros.")
    else:
        st.subheader("Quanto cada bandeira cobra a mais", anchor=False)
        fig = go.Figure(go.Bar(x=premio, y=premio.index, orientation="h", marker_color=AZUL,
                               text=[brl(v) for v in premio], textposition="outside",
                               hovertemplate="%{y}: %{text}<extra></extra>"))
        layout(fig, altura=300, xaxis_title=f"R$ a mais por {unidade} que a bandeira branca", hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        como_ler("cada barra compara postos da bandeira com postos de bandeira branca na mesma cidade e no "
                 "mesmo mês, nos últimos 12 meses do período.")
        quadro("bolso", "bandeira", "No seu bolso",
               f"Num tanque de {tanque} {sigla}, escolher um posto {premio.idxmax()} em vez de um de bandeira "
               f"branca da mesma cidade custa, em média, {brl(tanque * premio.max())} a mais.")

with direita:
    if correl is None:
        aviso("São necessárias ao menos 8 cidades para comparar concorrência e preço. Amplie a região.")
    else:
        if correl <= -0.3:
            titulo = "Cidades com mais postos tendem a ter preço menor"
        elif correl >= 0.3:
            titulo = "Cidades com mais postos tendem a ter preço maior"
        else:
            titulo = "Ter mais postos na cidade quase não muda o preço"
        st.subheader(titulo, anchor=False)
        inclinacao, intercepto = np.polyfit(np.log10(mun["postos"]), mun["preco_medio"], 1)
        xs = np.geomspace(mun["postos"].min(), mun["postos"].max(), 20)
        fig = go.Figure([
            go.Scatter(x=mun["postos"], y=mun["preco_medio"], mode="markers", name="Cidades",
                       marker=dict(color=AZUL, size=8, opacity=0.6, line=dict(color="white", width=1)),
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

# ---------------------------------------------------------------- como foi feito
st.divider()
secao(None, "metodo", "Transparência", "Como esta reportagem foi feita")
texto(f"Os preços vêm do Levantamento de Preços de Combustíveis da ANP, uma pesquisa semanal que, nos últimos "
      f"6 meses, visitou postos em {municipios[['uf', 'municipio']].drop_duplicates().shape[0]} cidades. Juntamos {num(mensal_uf['coletas'].sum() / 1e6, 1)} milhões de registros de "
      f"{rotulo_mes(meses[0])} a {rotulo_mes(meses[-1])}, tratados em SQL (DuckDB), e os cruzamos com o IPCA e o "
      "dólar do Banco Central e com o petróleo Brent (Ipeadata). Todo o código está aberto.")
metodo, glossario, limites = st.columns(3, gap="large")
with metodo.expander("Metodologia"):
    texto("- Médias mensais ponderadas pelo número de preços coletados.\n"
          "- Preço real: valores corrigidos pelo IPCA para reais do último mês.\n"
          "- Prêmio de bandeira: diferença para a bandeira branca na mesma cidade e mês.\n"
          "- Atraso do petróleo: correlação entre as variações mensais do Brent e da bomba, de 0 a 6 meses depois.")
with glossario.expander("Glossário"):
    texto("- **IPCA:** índice oficial de inflação do país.\n"
          "- **Brent:** petróleo de referência no mercado internacional.\n"
          "- **Bandeira branca:** posto sem contrato de marca com distribuidora.\n"
          "- **Paridade:** preço do etanol dividido pelo da gasolina.\n"
          "- **Correlação:** de −1 a 1, o quanto duas séries andam juntas.")
with limites.expander("Limitações"):
    texto("- A ANP pesquisa uma amostra de postos, não todos.\n"
          "- Correlação não prova causa: o petróleo é um fator, não o único.\n"
          "- Cidades com menos de 3 postos pesquisados ficam fora do gráfico de concorrência.")

html(f'<p class="fim"><small>{FONTE} Reportagem e código: Sara Alencar · '
     f'<a href="{REPOSITORIO}">ver o código no GitHub</a></small></p>')
