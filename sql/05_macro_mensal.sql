-- Indicadores macro mensais: IPCA acumulado (para deflacionar), dólar e Brent em reais.
WITH ipca AS (
    SELECT
        date_trunc('month', data)::DATE AS mes,
        -- índice encadeado: produto acumulado de (1 + variação mensal)
        exp(sum(ln(1 + valor / 100)) OVER (ORDER BY data)) AS ipca_indice
    FROM raw_ipca
),
dolar AS (
    SELECT date_trunc('month', data)::DATE AS mes, avg(valor) AS dolar
    FROM raw_dolar
    GROUP BY 1
),
brent AS (
    SELECT date_trunc('month', data)::DATE AS mes, avg(valor) AS brent_usd
    FROM raw_brent
    GROUP BY 1
)
SELECT
    ipca.mes,
    ipca.ipca_indice,
    dolar.dolar,
    brent.brent_usd,
    brent.brent_usd * dolar.dolar AS brent_brl
FROM ipca
LEFT JOIN dolar USING (mes)
LEFT JOIN brent USING (mes)
ORDER BY ipca.mes;
