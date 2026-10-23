-- Preço mensal por grupo de bandeira e o prêmio pago em relação à bandeira branca.
-- O prêmio é calculado dentro do mesmo município e mês, para não confundir
-- "bandeira mais cara" com "região mais cara".
WITH base AS (
    SELECT mes, regiao, uf, municipio, produto, grupo_bandeira,
           avg(preco) AS preco,
           count(*)   AS coletas
    FROM stg_precos
    GROUP BY ALL
),
branca AS (
    SELECT mes, uf, municipio, produto, preco AS preco_branca
    FROM base
    WHERE grupo_bandeira = 'Bandeira branca'
)
SELECT
    b.mes,
    b.regiao,
    b.uf,
    b.produto,
    b.grupo_bandeira,
    sum(b.preco * b.coletas) / sum(b.coletas) AS preco_medio,
    sum(b.coletas)                            AS coletas,
    sum((b.preco - br.preco_branca) * b.coletas)
        / nullif(sum(CASE WHEN br.preco_branca IS NOT NULL THEN b.coletas END), 0) AS premio_vs_branca
FROM base AS b
LEFT JOIN branca AS br USING (mes, uf, municipio, produto)
GROUP BY ALL
ORDER BY b.mes, b.uf, b.produto, b.grupo_bandeira;
