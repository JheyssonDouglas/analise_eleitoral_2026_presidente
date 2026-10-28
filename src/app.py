
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

RAIZ = Path(__file__).resolve().parent.parent
SAIDAS = RAIZ / "saidas"

ARQ_VOTOS = (SAIDAS / "votos_presidente_por_secao.csv").as_posix()
ARQ_RESUMO = (SAIDAS / "resumo_secoes_presidente.csv").as_posix()

LULA = "LUIZ INÁCIO LULA DA SILVA"
FLAVIO = "FLAVIO NANTES BOLSONARO"

COR_LULA = "#E5243B"
COR_FLAVIO = "#244A9B"

st.set_page_config(
    page_title="Análise de votação por seção",
    layout="wide"
)

st.title("Análise de votação por seção")
st.caption("Painel de análise dos dados processados do TSE")

if not (SAIDAS / "votos_presidente_por_secao.csv").exists():
    st.error(f"Arquivo não encontrado: {ARQ_VOTOS}")
    st.stop()

if not (SAIDAS / "resumo_secoes_presidente.csv").exists():
    st.error(f"Arquivo não encontrado: {ARQ_RESUMO}")
    st.stop()


@st.cache_resource
def conectar_banco():
    banco = duckdb.connect(
        database=":memory:",
        read_only=False
    )

    caminho_votos = ARQ_VOTOS.replace("'", "''")
    caminho_resumo = ARQ_RESUMO.replace("'", "''")

    banco.execute(f"""
        CREATE VIEW votos AS
        SELECT *
        FROM read_csv_auto('{caminho_votos}', header=true)
    """)

    banco.execute(f"""
        CREATE VIEW resumo AS
        SELECT *
        FROM read_csv_auto('{caminho_resumo}', header=true)
    """)

    return banco


con = conectar_banco()

def consultar(sql, parametros=None):
    """Executa uma consulta em um cursor independente e retorna um DataFrame."""
    cursor = con.cursor()
    try:
        if parametros is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, parametros)
        return cursor.fetchdf()
    finally:
        cursor.close()

# ==========================================================
# FILTROS
# ==========================================================

st.header("Filtros")

ufs = consultar("""
    SELECT DISTINCT SG_UF
    FROM resumo
    ORDER BY SG_UF
""")["SG_UF"].tolist()

turnos = consultar("""
    SELECT DISTINCT NR_TURNO
    FROM resumo
    ORDER BY NR_TURNO
""")["NR_TURNO"].tolist()

col1, col2, col3 = st.columns(3)

with col1:
    turno = st.selectbox("Turno da análise individual", turnos)

with col2:
    uf = st.selectbox("UF", ["Todas"] + ufs)

with col3:
    candidato = st.selectbox(
        "Candidato da análise individual",
        [LULA, FLAVIO]
    )

# Municípios disponíveis
filtro_uf = "" if uf == "Todas" else "AND SG_UF = ?"

sql_municipios = f"""
    SELECT DISTINCT NM_MUNICIPIO
    FROM resumo
    WHERE NR_TURNO = ?
    {filtro_uf}
    ORDER BY NM_MUNICIPIO
"""

params_municipios = [turno]

if uf != "Todas":
    params_municipios.append(uf)

municipios = consultar(
    sql_municipios, params_municipios
)["NM_MUNICIPIO"].tolist()

col4, col5, col6 = st.columns(3)

with col4:
    municipio = st.selectbox("Município", ["Todos"] + municipios)

# Zonas disponíveis
filtro_municipio = (
    "" if municipio == "Todos" else "AND NM_MUNICIPIO = ?"
)

sql_zonas = f"""
    SELECT DISTINCT NR_ZONA
    FROM resumo
    WHERE NR_TURNO = ?
    {filtro_uf}
    {filtro_municipio}
    ORDER BY NR_ZONA
"""

params_zonas = [turno]

if uf != "Todas":
    params_zonas.append(uf)

if municipio != "Todos":
    params_zonas.append(municipio)

zonas = consultar(
    sql_zonas, params_zonas
)["NR_ZONA"].tolist()

with col5:
    zona = st.selectbox("Zona eleitoral", ["Todas"] + zonas)

# Seções disponíveis
filtro_zona = "" if zona == "Todas" else "AND NR_ZONA = ?"

sql_secoes = f"""
    SELECT DISTINCT NR_SECAO
    FROM resumo
    WHERE NR_TURNO = ?
    {filtro_uf}
    {filtro_municipio}
    {filtro_zona}
    ORDER BY NR_SECAO
"""

params_secoes = [turno]

if uf != "Todas":
    params_secoes.append(uf)

if municipio != "Todos":
    params_secoes.append(municipio)

if zona != "Todas":
    params_secoes.append(zona)

secoes = consultar(
    sql_secoes, params_secoes
)["NR_SECAO"].tolist()

with col6:
    secoes_selecionadas = st.multiselect(
        "Seções eleitorais",
        options=secoes,
        placeholder="Todas as seções",
        help="Selecione uma ou mais seções. Se deixar vazio, todas serão consideradas."
    )

# Filtros geográficos usados pelas consultas
filtro_r_uf = "" if uf == "Todas" else "AND r.SG_UF = ?"
filtro_r_municipio = (
    "" if municipio == "Todos" else "AND r.NM_MUNICIPIO = ?"
)
filtro_r_zona = "" if zona == "Todas" else "AND r.NR_ZONA = ?"
filtro_r_secao = (
    "AND r.NR_SECAO IN ("
    + ", ".join(["?"] * len(secoes_selecionadas))
    + ")"
    if secoes_selecionadas
    else ""
)

params_geo = []

if uf != "Todas":
    params_geo.append(uf)

if municipio != "Todos":
    params_geo.append(municipio)

if zona != "Todas":
    params_geo.append(zona)

# Adiciona todas as seções selecionadas aos parâmetros das consultas.
# Quando nenhuma seção é selecionada, o filtro não restringe as seções.
if secoes_selecionadas:
    params_geo.extend(secoes_selecionadas)


# ==========================================================
# MAPA DO BRASIL POR ESTADO
# Inserir antes de "1. ANÁLISE INDIVIDUAL"
# ==========================================================

import requests

st.divider()
st.header("Visão geral do Brasil")

turno_mapa = st.selectbox(
    "Turno exibido no mapa",
    [1, 2],
    format_func=lambda x: f"{x}º turno",
    key="turno_mapa"
)

metrica_mapa = st.selectbox(
    "Indicador do mapa",
    [
        "Votos de Lula",
        "Votos de Flávio",
        "Diferença entre candidatos",
        "Comparecimento (%)",
        "Abstenção (%)"
    ],
    key="metrica_mapa"
)

# Nomes completos dos estados para relacionar o GeoJSON
nomes_ufs = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO"
}

@st.cache_data(ttl=86400)
def carregar_geojson():
    url = (
        "https://raw.githubusercontent.com/"
        "codeforgermany/click_that_hood/main/public/data/"
        "brazil-states.geojson"
    )
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta.json()

try:
    geojson = carregar_geojson()

    # Os votos são agregados diretamente no DuckDB.
    votos_uf = consultar("""
        SELECT
            SG_UF,
            SUM(CASE WHEN NM_VOTAVEL = ? THEN QT_VOTOS ELSE 0 END)
                AS VOTOS_LULA,
            SUM(CASE WHEN NM_VOTAVEL = ? THEN QT_VOTOS ELSE 0 END)
                AS VOTOS_FLAVIO
        FROM votos
        WHERE NR_TURNO = ?
          AND NM_VOTAVEL IN (?, ?)
        GROUP BY SG_UF
    """, [LULA, FLAVIO, turno_mapa, LULA, FLAVIO])

    # Indicadores de comparecimento e abstenção vêm do resumo
    # e são agregados sem juntar diretamente à tabela de votos.
    resumo_uf = consultar("""
        SELECT
            SG_UF,
            SUM(QT_APTOS) AS APTOS,
            SUM(QT_COMPARECIMENTO) AS COMPARECIMENTO,
            SUM(QT_ABSTENCOES) AS ABSTENCOES
        FROM resumo
        WHERE NR_TURNO = ?
        GROUP BY SG_UF
    """, [turno_mapa])

    mapa_df = resumo_uf.merge(votos_uf, on="SG_UF", how="left")
    mapa_df[["VOTOS_LULA", "VOTOS_FLAVIO"]] = (
        mapa_df[["VOTOS_LULA", "VOTOS_FLAVIO"]].fillna(0)
    )

    mapa_df["DIFERENCA"] = (
        mapa_df["VOTOS_LULA"] - mapa_df["VOTOS_FLAVIO"]
    )

    mapa_df["COMPARECIMENTO_PCT"] = (
        mapa_df["COMPARECIMENTO"]
        .div(mapa_df["APTOS"].replace(0, float("nan")))
        .mul(100)
    )

    mapa_df["ABSTENCAO_PCT"] = (
        mapa_df["ABSTENCOES"]
        .div(mapa_df["APTOS"].replace(0, float("nan")))
        .mul(100)
    )

    metricas = {
        "Votos de Lula": "VOTOS_LULA",
        "Votos de Flávio": "VOTOS_FLAVIO",
        "Diferença entre candidatos": "DIFERENCA",
        "Comparecimento (%)": "COMPARECIMENTO_PCT",
        "Abstenção (%)": "ABSTENCAO_PCT"
    }

    coluna_mapa = metricas[metrica_mapa]
    mapa_df["VALOR_MAPA"] = mapa_df[coluna_mapa]

    # A paleta muda conforme a métrica selecionada.
    if metrica_mapa == "Votos de Lula":
        escala = [[0, "#FADADD"], [1, "#E5243B"]]
    elif metrica_mapa == "Votos de Flávio":
        escala = [[0, "#D9E2F5"], [1, "#244A9B"]]
    elif metrica_mapa == "Diferença entre candidatos":
        escala = [
            [0, "#244A9B"],
            [0.5, "#F4F4F4"],
            [1, "#E5243B"]
        ]
    else:
        escala = [[0, "#F4F4F4"], [1, "#527A9B"]]

    # Relacionar as siglas aos nomes usados no GeoJSON.
    sigla_por_nome = {
        nome.upper(): sigla
        for nome, sigla in nomes_ufs.items()
    }

    # Também aceita propriedades que já contenham a sigla.
    for feature in geojson["features"]:
        propriedades = feature.get("properties", {})
        nome_geo = str(
            propriedades.get("name")
            or propriedades.get("name_pt")
            or propriedades.get("nome")
            or ""
        ).strip()

        sigla_geo = (
            propriedades.get("sigla")
            or propriedades.get("abbreviation")
            or propriedades.get("uf")
        )

        if sigla_geo:
            sigla_geo = str(sigla_geo).upper()
        else:
            sigla_geo = sigla_por_nome.get(nome_geo.upper())

        if sigla_geo:
            feature["properties"]["SIGLA_UF"] = sigla_geo

    # Criar um rótulo para mostrar valores no hover.
    mapa_df["VALOR_FORMATADO"] = mapa_df["VALOR_MAPA"].map(
        lambda x: (
            f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notna(x) else "Sem dados"
        )
    )

    fig_mapa = px.choropleth(
        mapa_df,
        geojson=geojson,
        locations="SG_UF",
        featureidkey="properties.SIGLA_UF",
        color="VALOR_MAPA",
        color_continuous_scale=escala,
        hover_name="SG_UF",
        hover_data={
            "VOTOS_LULA": ":,.0f",
            "VOTOS_FLAVIO": ":,.0f",
            "COMPARECIMENTO_PCT": ":.2f",
            "ABSTENCAO_PCT": ":.2f",
            "VALOR_MAPA": False,
            "SG_UF": False
        },
        labels={
            "VOTOS_LULA": "Votos de Lula",
            "VOTOS_FLAVIO": "Votos de Flávio",
            "COMPARECIMENTO_PCT": "Comparecimento (%)",
            "ABSTENCAO_PCT": "Abstenção (%)",
            "VALOR_MAPA": metrica_mapa
        },
        title=f"{metrica_mapa} — {turno_mapa}º turno"
    )

    fig_mapa.update_geos(
        fitbounds="locations",
        visible=False,
        showcountries=False
    )

    fig_mapa.update_layout(
        height=650,
        margin={"r": 0, "t": 60, "l": 0, "b": 0},
        coloraxis_colorbar_title=metrica_mapa
    )

    st.plotly_chart(fig_mapa, use_container_width=True)

    st.caption(
        "O mapa apresenta totais estaduais do turno escolhido. "
        "A diferença é calculada como votos de Lula menos votos de Flávio."
    )

    st.subheader("Dados por estado")

    tabela_mapa = mapa_df.rename(columns={
        "SG_UF": "UF",
        "VOTOS_LULA": "Votos Lula",
        "VOTOS_FLAVIO": "Votos Flávio",
        "DIFERENCA": "Diferença Lula - Flávio",
        "APTOS": "Eleitores aptos",
        "COMPARECIMENTO": "Comparecimento",
        "ABSTENCOES": "Abstenções",
        "COMPARECIMENTO_PCT": "Comparecimento (%)",
        "ABSTENCAO_PCT": "Abstenção (%)"
    })

    st.dataframe(
        tabela_mapa[
            [
                "UF",
                "Votos Lula",
                "Votos Flávio",
                "Diferença Lula - Flávio",
                "Eleitores aptos",
                "Comparecimento",
                "Abstenções",
                "Comparecimento (%)",
                "Abstenção (%)"
            ]
        ].sort_values("UF"),
        use_container_width=True,
        hide_index=True
    )

except Exception as erro:
    st.error(
        "Não foi possível carregar o mapa. "
        "Verifique sua conexão com a internet e tente novamente."
    )
    st.exception(erro)



# # ==========================================================
# # MAPA MUNICIPAL E ANÁLISE POR ZONA
# # ==========================================================

# import unicodedata

# st.divider()
# st.header("Mapa municipal e análise por zona")

# @st.cache_data(ttl=86400)

# @st.cache_data(ttl=86400)
# def carregar_malha_municipal(uf_sigla):
#     url_malha = (
#         "https://servicodados.ibge.gov.br/api/v3/malhas/estados/"
#         f"{uf_sigla}?intrarregiao=municipio"
#         "&formato=application/vnd.geo+json&qualidade=minima"
#     )

#     resp_malha = requests.get(url_malha, timeout=60)
#     resp_malha.raise_for_status()
#     geo = resp_malha.json()

#     url_municipios = (
#         "https://servicodados.ibge.gov.br/api/v1/localidades/"
#         f"estados/{uf_sigla}/municipios"
#     )

#     resp_municipios = requests.get(url_municipios, timeout=60)
#     resp_municipios.raise_for_status()
#     lista = resp_municipios.json()

#     nomes_por_codigo = {
#         str(m["id"]).zfill(7): m["nome"]
#         for m in lista
#     }

#     for feature in geo["features"]:
#         propriedades = feature.setdefault("properties", {})

#         codigo = str(
#             feature.get("id")
#             or propriedades.get("codarea")
#             or propriedades.get("CD_MUN")
#             or ""
#         ).strip()

#         codigo = codigo.zfill(7) if codigo.isdigit() else codigo

#         feature["id"] = codigo
#         propriedades["COD_IBGE"] = codigo
#         propriedades["MUNICIPIO"] = nomes_por_codigo.get(
#             codigo,
#             propriedades.get("NM_MUN", codigo)
#         )

#     return geo, lista



# def normalizar_nome(valor):
#     valor = unicodedata.normalize("NFKD", str(valor))
#     valor = "".join(
#         c for c in valor
#         if not unicodedata.combining(c)
#     )
#     return " ".join(valor.upper().split())


# uf_mapa_municipal = st.selectbox(
#     "Estado para explorar os municípios",
#     ufs,
#     key="uf_mapa_municipal"
# )

# turno_mapa_municipal = st.selectbox(
#     "Turno do mapa municipal",
#     [1, 2],
#     format_func=lambda x: f"{x}º turno",
#     key="turno_mapa_municipal"
# )

# metrica_municipal = st.selectbox(
#     "Indicador municipal",
#     [
#         "Votos de Lula",
#         "Votos de Flávio",
#         "Diferença Lula - Flávio"
#     ],
#     key="metrica_municipal"
# )

# try:
#     geo_municipios, lista_municipios = carregar_malha_municipal(
#         uf_mapa_municipal
#     )

#     # Votos dos dois candidatos, agregados por município.
#     votos_municipais = consultar("""
#         SELECT
#             NM_MUNICIPIO,
#             SUM(CASE
#                 WHEN NM_VOTAVEL = ? THEN QT_VOTOS ELSE 0
#             END) AS VOTOS_LULA,
#             SUM(CASE
#                 WHEN NM_VOTAVEL = ? THEN QT_VOTOS ELSE 0
#             END) AS VOTOS_FLAVIO
#         FROM votos
#         WHERE SG_UF = ?
#           AND NR_TURNO = ?
#           AND NM_VOTAVEL IN (?, ?)
#         GROUP BY NM_MUNICIPIO
#     """, [
#         LULA, FLAVIO, uf_mapa_municipal, turno_mapa_municipal,
#         LULA, FLAVIO
#     ])

#     resumo_municipal = consultar("""
#         SELECT
#             NM_MUNICIPIO,
#             SUM(QT_APTOS) AS APTOS,
#             SUM(QT_COMPARECIMENTO) AS COMPARECIMENTO,
#             SUM(QT_ABSTENCOES) AS ABSTENCOES
#         FROM resumo
#         WHERE SG_UF = ?
#           AND NR_TURNO = ?
#         GROUP BY NM_MUNICIPIO
#     """, [uf_mapa_municipal, turno_mapa_municipal])

#     dados_municipais = resumo_municipal.merge(
#         votos_municipais,
#         on="NM_MUNICIPIO",
#         how="left"
#     )

#     dados_municipais[["VOTOS_LULA", "VOTOS_FLAVIO"]] = (
#         dados_municipais[["VOTOS_LULA", "VOTOS_FLAVIO"]]
#         .fillna(0)
#     )

#     dados_municipais["DIFERENCA"] = (
#         dados_municipais["VOTOS_LULA"]
#         - dados_municipais["VOTOS_FLAVIO"]
#     )

#     # Relacionar os nomes usados nos CSVs aos códigos IBGE.
#     dados_municipais["NOME_CHAVE"] = (
#         dados_municipais["NM_MUNICIPIO"].map(normalizar_nome)
#     )

    
#     codigos = pd.DataFrame([
#         {
#             "COD_IBGE": str(m["id"]).zfill(7),
#             "NOME_CHAVE": normalizar_nome(m["nome"])
#         }
#         for m in lista_municipios
#     ])


#     dados_municipais = dados_municipais.merge(
#         codigos,
#         on="NOME_CHAVE",
#         how="left"
#     )

#     dados_municipais = dados_municipais.dropna(
#         subset=["COD_IBGE"]
#     )

#     coluna_valor = {
#         "Votos de Lula": "VOTOS_LULA",
#         "Votos de Flávio": "VOTOS_FLAVIO",
#         "Diferença Lula - Flávio": "DIFERENCA"
#     }[metrica_municipal]

#     if metrica_municipal == "Votos de Lula":
#         escala_municipal = [[0, "#FADADD"], [1, COR_LULA]]
#     elif metrica_municipal == "Votos de Flávio":
#         escala_municipal = [[0, "#D9E2F5"], [1, COR_FLAVIO]]
#     else:
#         escala_municipal = [
#             [0, COR_FLAVIO],
#             [0.5, "#F4F4F4"],
#             [1, COR_LULA]
#         ]

#     st.write("Diagnóstico da malha municipal")

#     st.write(
#         "Primeiro código do GeoJSON:",
#         geo_municipios["features"][0].get("properties", {}).get("COD_IBGE")
#     )

#     st.write(
#         "Primeiros códigos dos dados:",
#         dados_municipais["COD_IBGE"].head(10).tolist()
#     )

#     st.write(
#         "Total de municípios na malha:",
#         len(geo_municipios["features"])
#     )

#     st.write(
#         "Total de municípios associados aos dados:",
#         dados_municipais["COD_IBGE"].notna().sum()
#     )

#     fig_municipios = px.choropleth(
#         dados_municipais,
#         geojson=geo_municipios,
#         locations="COD_IBGE",
#         featureidkey="id",
#         color=coluna_valor,
#         color_continuous_scale=escala_municipal,
#         hover_name="NM_MUNICIPIO",
#         hover_data={
#             "VOTOS_LULA": ":,.0f",
#             "VOTOS_FLAVIO": ":,.0f",
#             "DIFERENCA": ":,.0f",
#             "COD_IBGE": False,
#             "NOME_CHAVE": False
#         },
#         labels={
#             "VOTOS_LULA": "Votos de Lula",
#             "VOTOS_FLAVIO": "Votos de Flávio",
#             "DIFERENCA": "Diferença Lula - Flávio"
#         },
#         title=(
#             f"{metrica_municipal} por município — "
#             f"{uf_mapa_municipal}, {turno_mapa_municipal}º turno"
#         )
#     )

#     fig_municipios.update_geos(
#         fitbounds="geojson",
#         visible=False,
#         showcountries=False,
#         showcoastlines=False,
#         showframe=False
#     )

#     fig_municipios.update_layout(
#         height=650,
#         margin={"r": 0, "t": 60, "l": 0, "b": 0}
#     )

#     st.plotly_chart(
#         fig_municipios,
#         use_container_width=True
#     )

#     # ======================================================
#     # RESUMO POR ZONA DENTRO DO MUNICÍPIO
#     # ======================================================

#     st.subheader("Comparação por zona eleitoral")

#     municipios_disponiveis = sorted(
#         dados_municipais["NM_MUNICIPIO"].dropna().unique().tolist()
#     )

#     municipio_zonas = st.selectbox(
#         "Município para detalhar as zonas",
#         municipios_disponiveis,
#         key="municipio_zonas"
#     )

#     comparacao_zonas = consultar("""
#         SELECT
#             r.NR_ZONA,

#             SUM(CASE
#                 WHEN r.NR_TURNO = 1 AND v.NM_VOTAVEL = ?
#                 THEN v.QT_VOTOS ELSE 0
#             END) AS LULA_1_TURNO,

#             SUM(CASE
#                 WHEN r.NR_TURNO = 2 AND v.NM_VOTAVEL = ?
#                 THEN v.QT_VOTOS ELSE 0
#             END) AS LULA_2_TURNO,

#             SUM(CASE
#                 WHEN r.NR_TURNO = 1 AND v.NM_VOTAVEL = ?
#                 THEN v.QT_VOTOS ELSE 0
#             END) AS FLAVIO_1_TURNO,

#             SUM(CASE
#                 WHEN r.NR_TURNO = 2 AND v.NM_VOTAVEL = ?
#                 THEN v.QT_VOTOS ELSE 0
#             END) AS FLAVIO_2_TURNO

#         FROM resumo r
#         LEFT JOIN votos v
#           ON r.NR_TURNO = v.NR_TURNO
#          AND r.SG_UF = v.SG_UF
#          AND r.CD_MUNICIPIO = v.CD_MUNICIPIO
#          AND r.NR_ZONA = v.NR_ZONA
#          AND r.NR_SECAO = v.NR_SECAO
#          AND v.NM_VOTAVEL IN (?, ?)

#         WHERE r.SG_UF = ?
#           AND r.NM_MUNICIPIO = ?
#           AND r.NR_TURNO IN (1, 2)

#         GROUP BY r.NR_ZONA
#         ORDER BY r.NR_ZONA
#     """, [
#         LULA, LULA, FLAVIO, FLAVIO,
#         LULA, FLAVIO,
#         uf_mapa_municipal, municipio_zonas
#     ])

#     comparacao_zonas["DIF_LULA"] = (
#         comparacao_zonas["LULA_2_TURNO"]
#         - comparacao_zonas["LULA_1_TURNO"]
#     )

#     comparacao_zonas["DIF_FLAVIO"] = (
#         comparacao_zonas["FLAVIO_2_TURNO"]
#         - comparacao_zonas["FLAVIO_1_TURNO"]
#     )

#     st.dataframe(
#         comparacao_zonas,
#         use_container_width=True,
#         hide_index=True
#     )

#     st.download_button(
#         "Exportar comparação por zona",
#         data=comparacao_zonas.to_csv(
#             index=False
#         ).encode("utf-8-sig"),
#         file_name="comparacao_por_zona.csv",
#         mime="text/csv",
#         key="download_zonas"
#     )

# except Exception as erro:
#     st.error(
#         "Não foi possível carregar a malha municipal ou os dados "
#         "por zona. Confira a conexão e os dados disponíveis."
#     )
#     st.exception(erro)



# ==========================================================
# 1. ANÁLISE INDIVIDUAL
# ==========================================================

st.divider()
st.header("1. Análise individual")

sql_individual = f"""
    SELECT
        r.NR_TURNO,
        r.SG_UF,
        r.NM_MUNICIPIO,
        r.NR_ZONA,
        r.NR_SECAO,
        r.QT_APTOS,
        r.QT_COMPARECIMENTO,
        r.QT_ABSTENCOES,
        r.QT_VOTOS_NOMINAIS,
        r.QT_VOTOS_BRANCOS,
        r.QT_VOTOS_NULOS,
        COALESCE(v.QT_VOTOS, 0) AS VOTOS_CANDIDATO
    FROM resumo r
    LEFT JOIN votos v
      ON r.NR_TURNO = v.NR_TURNO
     AND r.SG_UF = v.SG_UF
     AND r.CD_MUNICIPIO = v.CD_MUNICIPIO
     AND r.NR_ZONA = v.NR_ZONA
     AND r.NR_SECAO = v.NR_SECAO
     AND v.NM_VOTAVEL = ?
    WHERE r.NR_TURNO = ?
    {filtro_r_uf}
    {filtro_r_municipio}
    {filtro_r_zona}
    {filtro_r_secao}
    ORDER BY r.SG_UF, r.NM_MUNICIPIO, r.NR_ZONA, r.NR_SECAO
"""

dados = consultar(
    sql_individual,
    [candidato, turno] + params_geo
)

somente_zero = st.checkbox(
    "Mostrar somente seções com zero votos registrados para o candidato"
)

dados_exibidos = dados.copy()

if somente_zero:
    dados_exibidos = dados_exibidos[
        dados_exibidos["VOTOS_CANDIDATO"] == 0
    ]

st.metric(
    "Seções exibidas",
    f"{len(dados_exibidos):,}".replace(",", ".")
)

st.dataframe(
    dados_exibidos,
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Exportar análise individual para CSV",
    data=dados_exibidos.to_csv(index=False).encode("utf-8-sig"),
    file_name="consulta_secoes.csv",
    mime="text/csv",
    key="download_individual"
)

# ==========================================================
# 2. COMPARAÇÃO DOS DOIS CANDIDATOS NOS DOIS TURNOS
# ==========================================================

st.divider()
st.header("2. Comparação entre candidatos e turnos")

st.caption(
    "Os votos são apresentados para as mesmas localizações "
    "em ambos os turnos. A comparação não depende do turno "
    "selecionado na análise individual."
)

# Agregar primeiro os registros por seção, turno e candidato.
# Isso evita duplicação de votos caso existam várias linhas
# para a mesma chave no arquivo de origem.
sql_comparacao = f"""
    WITH votos_agregados AS (
        SELECT
            NR_TURNO,
            SG_UF,
            CD_MUNICIPIO,
            NR_ZONA,
            NR_SECAO,
            NM_VOTAVEL,
            SUM(QT_VOTOS) AS QT_VOTOS
        FROM votos
        WHERE NM_VOTAVEL IN (?, ?)
          AND NR_TURNO IN (1, 2)
        GROUP BY
            NR_TURNO,
            SG_UF,
            CD_MUNICIPIO,
            NR_ZONA,
            NR_SECAO,
            NM_VOTAVEL
    ),
    base AS (
        SELECT
            r.NR_TURNO,
            r.SG_UF,
            r.CD_MUNICIPIO,
            r.NM_MUNICIPIO,
            r.NR_ZONA,
            r.NR_SECAO,
            COALESCE(v.NM_VOTAVEL, '') AS NM_VOTAVEL,
            COALESCE(v.QT_VOTOS, 0) AS QT_VOTOS
        FROM resumo r
        LEFT JOIN votos_agregados v
          ON r.NR_TURNO = v.NR_TURNO
         AND r.SG_UF = v.SG_UF
         AND r.CD_MUNICIPIO = v.CD_MUNICIPIO
         AND r.NR_ZONA = v.NR_ZONA
         AND r.NR_SECAO = v.NR_SECAO
        WHERE r.NR_TURNO IN (1, 2)
          {filtro_r_uf}
          {filtro_r_municipio}
          {filtro_r_zona}
          {filtro_r_secao}
    )
    SELECT
        SG_UF,
        CD_MUNICIPIO,
        NM_MUNICIPIO,
        NR_ZONA,
        NR_SECAO,

        SUM(CASE
            WHEN NR_TURNO = 1 AND NM_VOTAVEL = ?
            THEN QT_VOTOS ELSE 0
        END) AS LULA_1_TURNO,

        SUM(CASE
            WHEN NR_TURNO = 2 AND NM_VOTAVEL = ?
            THEN QT_VOTOS ELSE 0
        END) AS LULA_2_TURNO,

        SUM(CASE
            WHEN NR_TURNO = 1 AND NM_VOTAVEL = ?
            THEN QT_VOTOS ELSE 0
        END) AS FLAVIO_1_TURNO,

        SUM(CASE
            WHEN NR_TURNO = 2 AND NM_VOTAVEL = ?
            THEN QT_VOTOS ELSE 0
        END) AS FLAVIO_2_TURNO

    FROM base
    GROUP BY
        SG_UF,
        CD_MUNICIPIO,
        NM_MUNICIPIO,
        NR_ZONA,
        NR_SECAO
    ORDER BY
        SG_UF,
        NM_MUNICIPIO,
        NR_ZONA,
        NR_SECAO
"""

params_comparacao = [
    LULA,
    FLAVIO,
    *params_geo,
    LULA,
    LULA,
    FLAVIO,
    FLAVIO
]

comparacao = consultar(
    sql_comparacao, params_comparacao
)

if comparacao.empty:
    st.info("Nenhuma seção encontrada para os filtros selecionados.")

else:
    # Diferenças absolutas entre os turnos
    comparacao["DIF_LULA"] = (
        comparacao["LULA_2_TURNO"]
        - comparacao["LULA_1_TURNO"]
    )

    comparacao["DIF_FLAVIO"] = (
        comparacao["FLAVIO_2_TURNO"]
        - comparacao["FLAVIO_1_TURNO"]
    )

    # Variações percentuais; indefinidas quando o primeiro
    # turno tem zero votos.
    comparacao["VAR_LULA_PCT"] = (
        comparacao["DIF_LULA"]
        .div(comparacao["LULA_1_TURNO"].replace(0, float("nan")))
        .mul(100)
    )

    comparacao["VAR_FLAVIO_PCT"] = (
        comparacao["DIF_FLAVIO"]
        .div(comparacao["FLAVIO_1_TURNO"].replace(0, float("nan")))
        .mul(100)
    )

    # Totais do recorte geográfico
    total_lula_1 = int(comparacao["LULA_1_TURNO"].sum())
    total_lula_2 = int(comparacao["LULA_2_TURNO"].sum())
    total_flavio_1 = int(comparacao["FLAVIO_1_TURNO"].sum())
    total_flavio_2 = int(comparacao["FLAVIO_2_TURNO"].sum())

    # Indicadores em duas linhas
    st.subheader("Lula")

    a, b, c = st.columns(3)

    a.metric(
        "1º turno",
        f"{total_lula_1:,}".replace(",", ".")
    )

    b.metric(
        "2º turno",
        f"{total_lula_2:,}".replace(",", ".")
    )

    diferenca_lula_total = total_lula_2 - total_lula_1

    c.metric(
        "Diferença",
        f"{diferenca_lula_total:+,}".replace(",", ".")
    )

    if total_lula_1:
        st.caption(
            "Variação percentual de Lula: "
            f"{diferenca_lula_total / total_lula_1 * 100:+.2f}%"
        )
    else:
        st.caption(
            "Variação percentual de Lula indisponível: "
            "total do primeiro turno igual a zero."
        )

    st.subheader("Flávio")

    a, b, c = st.columns(3)

    a.metric(
        "1º turno",
        f"{total_flavio_1:,}".replace(",", ".")
    )

    b.metric(
        "2º turno",
        f"{total_flavio_2:,}".replace(",", ".")
    )

    diferenca_flavio_total = total_flavio_2 - total_flavio_1

    c.metric(
        "Diferença",
        f"{diferenca_flavio_total:+,}".replace(",", ".")
    )

    if total_flavio_1:
        st.caption(
            "Variação percentual de Flávio: "
            f"{diferenca_flavio_total / total_flavio_1 * 100:+.2f}%"
        )
    else:
        st.caption(
            "Variação percentual de Flávio indisponível: "
            "total do primeiro turno igual a zero."
        )

    # Tabela comparativa com nomes mais claros
    st.subheader("Tabela por seção")

    colunas_exibicao = {
        "SG_UF": "UF",
        "NM_MUNICIPIO": "Município",
        "NR_ZONA": "Zona",
        "NR_SECAO": "Seção",
        "LULA_1_TURNO": "Lula — 1º turno",
        "LULA_2_TURNO": "Lula — 2º turno",
        "DIF_LULA": "Diferença Lula",
        "VAR_LULA_PCT": "Variação Lula (%)",
        "FLAVIO_1_TURNO": "Flávio — 1º turno",
        "FLAVIO_2_TURNO": "Flávio — 2º turno",
        "DIF_FLAVIO": "Diferença Flávio",
        "VAR_FLAVIO_PCT": "Variação Flávio (%)"
    }

    tabela = comparacao[list(colunas_exibicao)].rename(
        columns=colunas_exibicao
    )

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Lula — 1º turno": st.column_config.NumberColumn(
                format="%d"
            ),
            "Lula — 2º turno": st.column_config.NumberColumn(
                format="%d"
            ),
            "Diferença Lula": st.column_config.NumberColumn(
                format="%+d"
            ),
            "Variação Lula (%)": st.column_config.NumberColumn(
                format="%.2f%%"
            ),
            "Flávio — 1º turno": st.column_config.NumberColumn(
                format="%d"
            ),
            "Flávio — 2º turno": st.column_config.NumberColumn(
                format="%d"
            ),
            "Diferença Flávio": st.column_config.NumberColumn(
                format="%+d"
            ),
            "Variação Flávio (%)": st.column_config.NumberColumn(
                format="%.2f%%"
            )
        }
    )

    # Gráfico de comparação dos totais
    st.subheader("Votos por candidato e turno")

    grafico_df = pd.DataFrame({
        "Candidato": [
            "Lula", "Lula", "Flávio", "Flávio"
        ],
        "Turno": [
            "1º turno", "2º turno", "1º turno", "2º turno"
        ],
        "Votos": [
            total_lula_1,
            total_lula_2,
            total_flavio_1,
            total_flavio_2
        ]
    })

    fig = px.bar(
        grafico_df,
        x="Candidato",
        y="Votos",
        color="Candidato",
        barmode="group",
        facet_col="Turno",
        text="Votos",
        color_discrete_map={
            "Lula": COR_LULA,
            "Flávio": COR_FLAVIO
        },
        title="Comparação dos votos registrados"
    )

    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        yaxis_title="Votos",
        xaxis_title="Candidato"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Gráfico por seção: mostrar somente quando o recorte
    # contém até 30 seções, para preservar a legibilidade.
    if len(comparacao) == 1:
        st.subheader("Comparação na seção selecionada")

        linha = comparacao.iloc[0]

        grafico_secao = pd.DataFrame({
            "Turno": [
                "1º turno", "2º turno",
                "1º turno", "2º turno"
            ],
            "Candidato": [
                "Lula", "Lula", "Flávio", "Flávio"
            ],
            "Votos": [
                linha["LULA_1_TURNO"],
                linha["LULA_2_TURNO"],
                linha["FLAVIO_1_TURNO"],
                linha["FLAVIO_2_TURNO"]
            ]
        })

        fig_secao = px.bar(
            grafico_secao,
            x="Turno",
            y="Votos",
            color="Candidato",
            barmode="group",
            text="Votos",
            color_discrete_map={
                "Lula": COR_LULA,
                "Flávio": COR_FLAVIO
            }
        )

        fig_secao.update_layout(yaxis_title="Votos")
        st.plotly_chart(fig_secao, use_container_width=True)

    elif len(comparacao) <= 30:
        st.subheader("Votos por seção")

        comparacao["LOCAL"] = (
            comparacao["NM_MUNICIPIO"].astype(str)
            + " — Z"
            + comparacao["NR_ZONA"].astype(str)
            + " / S"
            + comparacao["NR_SECAO"].astype(str)
        )

        grafico_secoes = comparacao.melt(
            id_vars=["LOCAL"],
            value_vars=[
                "LULA_1_TURNO",
                "LULA_2_TURNO",
                "FLAVIO_1_TURNO",
                "FLAVIO_2_TURNO"
            ],
            var_name="Série",
            value_name="Votos"
        )

        nomes_series = {
            "LULA_1_TURNO": "Lula — 1º turno",
            "LULA_2_TURNO": "Lula — 2º turno",
            "FLAVIO_1_TURNO": "Flávio — 1º turno",
            "FLAVIO_2_TURNO": "Flávio — 2º turno"
        }

        cores_series = {
            "Lula — 1º turno": COR_LULA,
            "Lula — 2º turno": "#F58A96",
            "Flávio — 1º turno": COR_FLAVIO,
            "Flávio — 2º turno": "#7895D4"
        }

        grafico_secoes["Série"] = grafico_secoes["Série"].map(
            nomes_series
        )

        fig_secoes = px.bar(
            grafico_secoes,
            x="LOCAL",
            y="Votos",
            color="Série",
            barmode="group",
            color_discrete_map=cores_series,
            title="Votos por seção e turno"
        )

        fig_secoes.update_layout(
            xaxis_title="Município / zona / seção",
            xaxis_tickangle=-45,
            yaxis_title="Votos"
        )

        st.plotly_chart(fig_secoes, use_container_width=True)

    else:
        st.info(
            "O recorte contém mais de 30 seções. "
            "Use município, zona ou seção para restringir a área "
            "e habilitar o gráfico detalhado por seção."
        )

    st.download_button(
        "Exportar comparação dos candidatos e turnos para CSV",
        data=comparacao.to_csv(index=False).encode("utf-8-sig"),
        file_name="comparacao_candidatos_turnos.csv",
        mime="text/csv",
        key="download_comparacao"
    )

st.caption(
    "Nota: zero significa que não foi encontrado registro do candidato "
    "na tabela de votos para aquela chave. Isso não comprova, por si só, "
    "ausência de votos ou irregularidade eleitoral."
)
