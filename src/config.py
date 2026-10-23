from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"

ANP_BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca"

# A ANP mudou o formato dos arquivos ao longo do tempo (csv até 2021, zip depois)
# e o 1º semestre de 2022 tem um nome fora do padrão.
ANP_URLS_ESPECIAIS = {
    (2022, 1): f"{ANP_BASE}/precos-semestrais-ca.zip",
}

PRIMEIRO_SEMESTRE = (2020, 1)

# Séries do Sistema Gerenciador de Séries Temporais (SGS) do Banco Central
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SERIE_IPCA = 433    # IPCA - variação mensal (%)
SERIE_DOLAR = 3698  # Dólar comercial (venda) - média mensal

# Petróleo Brent (US$/barril, diário), série da EIA republicada pelo Ipeadata
BRENT_URL = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='EIA366_PBRENT366')"

HEADERS = {"User-Agent": "Mozilla/5.0 (painel-combustiveis-anp; projeto de portfolio)"}

REGIOES = {
    "N": "Norte",
    "NE": "Nordeste",
    "CO": "Centro-Oeste",
    "SE": "Sudeste",
    "S": "Sul",
}

ESTADOS = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}

# Paridade a partir da qual a gasolina passa a compensar mais que o etanol
PARIDADE_LIMITE = 0.70
