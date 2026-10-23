# Painel de Combustíveis no Brasil (ANP)

![testes](https://github.com/saranlalencar/Projeto_Integrador/actions/workflows/testes.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.66-red)
![dados](https://img.shields.io/badge/dados-ANP%20%C2%B7%20BCB%20%C2%B7%20Ipeadata-0b6870)

Análise de **5,46 milhões de preços de combustíveis** coletados pela ANP em postos de todo o Brasil entre janeiro de 2020 e junho de 2026, cruzados com inflação (IPCA), dólar e petróleo Brent. O painel mostra quanto o preço subiu de verdade, o que move o preço na bomba, onde o etanol compensa e quanto se paga a mais por bandeira.

<!-- Depois do deploy, coloque aqui: **[Abrir o painel online](https://SEU-APP.streamlit.app)** -->
<!-- E um GIF de ~10 s navegando pelas abas: ![Painel](docs/painel.gif) -->

## Perguntas de negócio

1. A gasolina está mais cara hoje do que em 2020, descontada a inflação?
2. Com quanto atraso uma variação do petróleo chega à bomba?
3. Depois que o ICMS da gasolina virou um valor fixo por litro (jun/2023), a diferença de preço entre estados diminuiu?
4. Em quais estados o etanol compensa mais que a gasolina?
5. Postos de bandeira branca são mais baratos? Quanto?
6. Cidades com mais postos têm preço menor?

## Principais achados

Dados até jun/2026, gasolina comum, média Brasil.

- **Em termos reais, o preço ficou praticamente estável.** O litro foi de R$ 4,62 para R$ 6,66 (+44,2% nominal), mas, corrigido pelo IPCA, a alta é de apenas 0,5%. O pico foi em mai/2022: R$ 7,29 nominais, ou R$ 8,70 em valores de hoje.
- **O petróleo chega à bomba em cerca de 1 mês.** A variação do Brent em reais tem a maior correlação com a variação na bomba um mês depois (r = 0,40), contra 0,25 no mesmo mês.
- **O ICMS fixo por litro não reduziu a diferença entre estados.** O coeficiente de variação entre as UFs foi de 5,2% antes de jun/2023 e 5,6% depois. Frete e logística continuam pesando: Roraima (R$ 7,68) e Acre (R$ 7,46) são os mais caros; Minas Gerais (R$ 6,36), o mais barato.
- **O etanol compensa em 7 de 27 estados**, todos no Centro-Sul: Mato Grosso (57% do preço da gasolina), São Paulo (60%), Mato Grosso do Sul, Goiás, Distrito Federal, Paraná e Minas Gerais. No Amapá, o etanol custa 91% da gasolina.
- **Bandeira custa cerca de R$ 0,15 a mais por litro.** No mesmo município e mês, postos Ipiranga cobram R$ 0,15 a mais que os de bandeira branca, Raízen (Shell) R$ 0,15 e Vibra (BR) R$ 0,14.
- **Número de postos explica pouco o preço.** Entre 416 municípios, a correlação entre postos pesquisados e preço médio é de −0,10.

## O que tem no painel

| Aba | Conteúdo |
| --- | --- |
| Visão geral | Preço atual de gasolina, etanol e diesel S10 com variação no mês, paridade etanol/gasolina, preço nominal × real, mapa por estado, ranking de UFs |
| O que move o preço | Bomba, Brent em reais e IPCA no mesmo índice (base 100), correlação com defasagem, dispersão entre estados antes e depois do ICMS fixo |
| Etanol × gasolina | Mapa da paridade por UF, evolução da paridade, cidades onde o etanol mais compensa |
| Postos e bandeiras | Prêmio por bandeira em relação à branca, postos × preço por município, distribuição de preços, variação dentro de cada região |

Filtros: produto, região, estado e período.

## Como funciona

```
ANP (CSVs semestrais) ─┐
BCB: IPCA, dólar ──────┼─> src/extract.py ─> data/raw ─> src/transform.py + sql/*.sql (DuckDB) ─> data/processed/*.parquet ─> app.py (Streamlit + Plotly)
Ipeadata: Brent ───────┘
```

- **Extração** (`src/extract.py`): baixa os 13 semestres da série histórica da ANP (cerca de 1 GB) e as séries do Banco Central (API SGS) e do Ipeadata.
- **Transformação** (`sql/`): consultas SQL no DuckDB limpam os dados (tipos, CNPJ, preços implausíveis, datas inválidas), agrupam bandeiras e geram quatro tabelas: preço mensal por UF, prêmio por bandeira, retrato por município e indicadores macro. O prêmio por bandeira é calculado dentro do mesmo município para não confundir bandeira com região.
- **Painel** (`app.py`): lê apenas os Parquet processados (cerca de 1,3 MB, versionados no repositório), então o deploy não precisa baixar os dados brutos.
- **Testes** (`tests/`): 21 testes com pytest cobrem os cálculos, as regras de limpeza do SQL e a abertura do painel com diferentes filtros (Streamlit AppTest). Rodam no GitHub Actions a cada push.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt

streamlit run app.py            # usa os dados já processados

# para atualizar os dados:
python -m src.extract           # baixa ANP, IPCA, dólar e Brent
python -m src.transform         # recria data/processed
pytest -q
```

## Estrutura

```
app.py                  painel Streamlit
src/extract.py          download das fontes
src/transform.py        carga no DuckDB e execução dos SQL
src/metrics.py          cálculos (deflação, paridade, correlação com defasagem)
sql/                    camada staging e tabelas finais
data/processed/         tabelas Parquet usadas pelo painel
tests/                  pytest
```

## Fontes

- [ANP: Série histórica de preços de combustíveis](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis)
- [Banco Central: SGS](https://www3.bcb.gov.br/sgspub/) · série 433 (IPCA) e 3698 (dólar)
- [Ipeadata](http://www.ipeadata.gov.br/): petróleo Brent (EIA)

A pesquisa da ANP é amostral: o número de postos por município é o de postos pesquisados, não o total existente.

## Licença

MIT
