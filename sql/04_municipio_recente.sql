-- Retrato dos últimos 6 meses por município: preço médio e quantos postos a ANP
-- pesquisou ali (a pesquisa é amostral, não é o total de postos da cidade).
WITH ultimo AS (SELECT max(mes) AS mes FROM stg_precos)
SELECT
    regiao,
    uf,
    municipio,
    produto,
    avg(preco)              AS preco_medio,
    count(DISTINCT cnpj)    AS postos,
    count(*)                AS coletas
FROM stg_precos, ultimo
WHERE stg_precos.mes > ultimo.mes - INTERVAL 6 MONTH
GROUP BY ALL;
