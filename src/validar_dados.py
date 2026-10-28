
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SAIDAS = RAIZ / "saidas"

votos = pd.read_csv(SAIDAS / "votos_presidente_por_secao.csv")
resumo = pd.read_csv(SAIDAS / "resumo_secoes_presidente.csv")

# Normaliza nomes para localizar os dois candidatos.
votos["CANDIDATO_NORMALIZADO"] = (
    votos["NM_VOTAVEL"].astype(str).str.upper().str.strip()
)

candidatos = {
    "LULA": "LUIZ INÁCIO LULA DA SILVA",
    "FLAVIO": "FLAVIO NANTES BOLSONARO",
}

print("\n=== TAMANHO DAS BASES ===")
print(f"Linhas de votos: {len(votos):,}")
print(f"Linhas de resumo: {len(resumo):,}")
print(f"Turnos encontrados: {sorted(votos['NR_TURNO'].unique())}")

print("\n=== VOTOS POR CANDIDATO E TURNO ===")
for apelido, nome in candidatos.items():
    encontrados = votos[
        votos["CANDIDATO_NORMALIZADO"] == nome
    ]

    if encontrados.empty:
        print(f"{apelido}: candidato não encontrado com o nome esperado.")
        print(
            votos.loc[
                votos["CANDIDATO_NORMALIZADO"].str.contains(
                    apelido, na=False
                ),
                "NM_VOTAVEL"
            ].drop_duplicates().tolist()
        )
    else:
        print(f"\n{apelido}")
        print(
            encontrados.groupby("NR_TURNO")["QT_VOTOS"]
            .sum()
            .to_string()
        )

# Cada linha do resumo deveria representar uma combinação única
# de turno, município, zona e seção.
chaves = [
    "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
    "NR_ZONA", "NR_SECAO"
]

print("\n=== DUPLICIDADES NO RESUMO ===")
print("Linhas duplicadas:", resumo.duplicated(chaves).sum())

print("\n=== SEÇÕES COM ZERO VOTOS PARA CANDIDATOS ===")
base = resumo[chaves].drop_duplicates()

for apelido, nome in candidatos.items():
    candidato = votos[
        votos["CANDIDATO_NORMALIZADO"] == nome
    ]

    por_secao = candidato.groupby(chaves, as_index=False)["QT_VOTOS"].sum()

    comparacao = base.merge(por_secao, on=chaves, how="left")
    comparacao["QT_VOTOS"] = comparacao["QT_VOTOS"].fillna(0)

    zeros = comparacao[comparacao["QT_VOTOS"] == 0]

    print(f"\n{apelido}: {len(zeros):,} seções sem votos registrados")
    print(zeros.head(10).to_string(index=False))

    zeros.to_csv(
        SAIDAS / f"secoes_zero_{apelido.lower()}.csv",
        index=False,
        encoding="utf-8-sig"
    )

print("\nValidação concluída.")
