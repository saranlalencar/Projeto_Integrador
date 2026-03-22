import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statistics as s
import streamlit as st
raw_data = pd.read_csv("Preços semestrais - AUTOMOTIVOS_2025.02.csv", sep=";")
columns_to_drop = ['CNPJ da Revenda', 'Nome da Rua','Numero Rua', 'Complemento', 'Unidade de Medida','Valor de Compra']
clean_data = raw_data.drop(columns=columns_to_drop)
clean_data["Valor de Venda"] = clean_data["Valor de Venda"].str.replace(",", ".")
clean_data["Valor de Venda"] = clean_data["Valor de Venda"].astype(float)

st.title("Análise por região")
st.divider()
st.header("Filtro por região")


regioes_estados = {
    "NORDESTE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "NORTE": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "SUL": ["PR", "RS", "SC"],
    "SUDESTE": ["ES", "MG", "RJ", "SP"],
    "CENTRO-OESTE": ["DF", "GO", "MT", "MS"]
}

## filtros

Regiao = st.selectbox ("Selecione uma região: ", ["Todas"] + list(regioes_estados.keys()))

df_resultado = clean_data.copy()

if Regiao == "Todas":
    Estados = ["Todos"] + clean_data["Estado - Sigla"].unique().tolist()
else:
    Estados = ["Todos"] + regioes_estados[Regiao]

## filtro estados
Estados_filtrados = st.selectbox("Selecione um Estado: ", Estados)

if Regiao != "Todas":
    df_resultado = df_resultado[df_resultado["Estado - Sigla"].isin(regioes_estados[Regiao])]

if Estados_filtrados != "Todos":
    df_resultado = df_resultado[df_resultado["Estado - Sigla"] == Estados_filtrados]

## filtro municipios

Municipio =  df_resultado["Municipio"].unique().tolist()

Municipio_filtrado = st.selectbox("Selecione um município: ", ["Todos"] + Municipio)

if Municipio_filtrado != "Todos":
     df_resultado = df_resultado[df_resultado["Municipio"]== Municipio_filtrado]


Bairro = df_resultado["Bairro"].unique().tolist()
Bairros_filtrados = st.selectbox("Selecione um bairro: ", ["Todos"] +Bairro)

if Bairros_filtrados != "Todos":
    df_resultado= df_resultado[df_resultado["Bairro"]==Bairros_filtrados]


Produtos = ["Todos"] + clean_data["Produto"].unique().tolist()
Produtos_filtrados = st.selectbox("Selecione um produto: ", Produtos)


if Produtos_filtrados != "Todos":
    df_resultado = df_resultado[df_resultado["Produto"]==Produtos_filtrados]

Bandeiras = ["Todas"] + clean_data["Bandeira"].unique().tolist()
Bandeiras_filtradas = st.selectbox("Selecione uma bandeira: ", Bandeiras)
if Bandeiras_filtradas != "Todas":
    df_resultado = df_resultado[df_resultado["Bandeira"]==Bandeiras_filtradas]

#st.dataframe(df_resultado)

df_agrupado = df_resultado.groupby([
    'Regiao - Sigla', 
    'Estado - Sigla', 
    'Municipio', 
    'Bairro', 
    'Produto',
    'Bandeira',
]).size().reset_index(name='Quantidade')

st.dataframe(df_agrupado)

st.divider()
st.header("Valores por região")

df_analise = df_resultado.groupby(
    ["Regiao - Sigla", "Estado - Sigla", "Municipio", "Bairro" ,"Bandeira"]
).agg({
    "Valor de Venda": ["median","max", "min"]
})

st.dataframe(df_analise)

st.divider()
st.header("Ranking")

df_ranking_menor_mediana = df_analise.sort_values(by=("Valor de Venda", "median"), ascending= True)
df_ranking_maior_mediana = df_analise.sort_values(by=("Valor de Venda", "median"), ascending= False)
st.dataframe  (df_ranking_menor_mediana.head(5))
st.dataframe (df_ranking_maior_mediana.head(5))

# fig, ax = plt.subplots(figsize=(10,6))

# # Top 5 baratos
# ax.barh(df_ranking_menor_mediana["Estado - Sigla"], 
#         df_ranking_menor_mediana[("Valor de Venda", "median")], 
#         color='skyblue', label='Mais Baratos')

# # Top 5 caros
# ax.barh(df_ranking_maior_mediana["Estado - Sigla"], 
#         df_ranking_maior_mediana[("Valor de Venda", "median")], 
#         color='tomato', label='Mais Caros')

# ax.set_xlabel("Mediana do Valor de Venda")
# ax.set_ylabel("Cidade/Bairro")
# ax.set_title("Top 5 Mais Caros e Mais Baratos")
# ax.legend()

# st.pyplot(fig)

#groupby









# print(clean_data.head())


