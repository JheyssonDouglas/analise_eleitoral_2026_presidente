
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDAS = RAIZ / "saidas"
SAIDAS.mkdir(exist_ok=True)

arquivo_votos = DADOS / "votacao_secao_2026" / "votacao_secao_2026_BR.csv"
arquivo_detalhe = (
    DADOS / "detalhes_votacao_secao_2026"
    / "detalhe_votacao_secao_2026_BRASIL.csv"
)

CHAVES = [
    "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
    "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO"
]


def processar_csv(caminho, colunas, filtro_presidente, agregacao):
    partes = []
    valores = agregacao["valor"]
    if isinstance(valores, str):
        valores = [valores]

    for bloco in pd.read_csv(
        caminho,
        sep=";",
        encoding="latin1",
        usecols=colunas,
        chunksize=200_000,
        low_memory=False
    ):
        bloco = bloco.loc[filtro_presidente(bloco)].copy()
        bloco["NR_TURNO"] = pd.to_numeric(
            bloco["NR_TURNO"], errors="coerce"
        )
        bloco = bloco[bloco["NR_TURNO"].isin([1, 2])]

        if bloco.empty:
            continue

        partes.append(
            bloco.groupby(agregacao["chaves"], as_index=False)[valores]
            .sum()
        )

    if not partes:
        raise ValueError(f"Nenhum registro encontrado em {caminho.name}")

    resultado = pd.concat(partes, ignore_index=True)

    return resultado.groupby(
        agregacao["chaves"], as_index=False
    )[valores].sum()



# 1. Votos por candidato, zona e seção
print("Processando votos dos candidatos...")

colunas_votos = CHAVES + [
    "CD_CARGO", "DS_CARGO", "NM_VOTAVEL", "QT_VOTOS"
]

votos = processar_csv(
    arquivo_votos,
    colunas_votos,
    lambda df: (
        df["DS_CARGO"].astype(str).str.contains(
            "Presidente", case=False, na=False
        )
    ),
    {
        "chaves": CHAVES + ["NM_VOTAVEL"],
        "valor": "QT_VOTOS"
    }
)

votos.to_csv(
    SAIDAS / "votos_presidente_por_secao.csv",
    index=False,
    encoding="utf-8-sig"
)

# 2. Totais de cada seção para presidente
print("Processando totais das seções...")

colunas_detalhe = CHAVES + [
    "CD_CARGO", "DS_CARGO",
    "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
    "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS"
]

detalhe = processar_csv(
    arquivo_detalhe,
    colunas_detalhe,
    lambda df: (
        df["DS_CARGO"].astype(str).str.contains(
            "Presidente", case=False, na=False
        )
    ),
    {
        "chaves": CHAVES,
        "valor": [
            "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
            "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS"
        ]
    }
)

# processar_csv usa soma e mantém as colunas numéricas do resumo.
detalhe.to_csv(
    SAIDAS / "resumo_secoes_presidente.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nConcluído!")
print("Arquivos gerados:")
print(SAIDAS / "votos_presidente_por_secao.csv")
print(SAIDAS / "resumo_secoes_presidente.csv")
print("\nAmostra de votos:")
print(votos.head())
print("\nAmostra de totais:")
print(detalhe.head())
