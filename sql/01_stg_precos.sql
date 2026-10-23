-- Camada staging: uma linha por coleta (posto × produto × data), com tipos corretos
-- e valores implausíveis removidos.
CREATE OR REPLACE TABLE stg_precos AS
WITH tipado AS (
    SELECT
        upper(trim(regiao))                                   AS regiao,
        upper(trim(uf))                                       AS uf,
        upper(trim(municipio))                                AS municipio,
        regexp_replace(cnpj, '[^0-9]', '', 'g')               AS cnpj,
        upper(trim(produto))                                  AS produto,
        try_strptime(data_coleta, '%d/%m/%Y')::DATE           AS data_coleta,
        try_cast(replace(valor_venda, ',', '.') AS DOUBLE)    AS preco,
        trim(unidade)                                         AS unidade,
        upper(trim(bandeira))                                 AS bandeira
    FROM raw_precos
)
SELECT
    *,
    date_trunc('month', data_coleta)::DATE AS mes,
    CASE
        WHEN bandeira LIKE '%PETROBRAS%' OR bandeira LIKE '%VIBRA%' THEN 'Vibra (BR)'
        WHEN bandeira LIKE '%IPIRANGA%'                             THEN 'Ipiranga'
        WHEN bandeira LIKE '%RAIZEN%' OR bandeira LIKE '%SHELL%'    THEN 'Raízen (Shell)'
        WHEN bandeira = 'BRANCA'                                    THEN 'Bandeira branca'
        ELSE 'Outras bandeiras'
    END AS grupo_bandeira
FROM tipado
WHERE data_coleta IS NOT NULL
  AND preco BETWEEN 0.5 AND 20;
