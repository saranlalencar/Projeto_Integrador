-- Preço mensal por UF e produto. É a tabela principal do painel.
SELECT
    mes,
    regiao,
    uf,
    produto,
    avg(preco)              AS preco_medio,
    median(preco)           AS preco_mediano,
    min(preco)              AS preco_min,
    max(preco)              AS preco_max,
    stddev_samp(preco)      AS preco_desvio,
    count(*)                AS coletas,
    count(DISTINCT cnpj)    AS postos
FROM stg_precos
GROUP BY ALL
ORDER BY mes, uf, produto;
