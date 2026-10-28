
from pathlib import Path
import pandas as pd

# Raiz do projeto, independentemente de onde o script for executado
RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"

arquivos_csv = list(PASTA_DADOS.rglob("*.csv"))

if not arquivos_csv:
    print(f"Nenhum CSV encontrado em: {PASTA_DADOS}")
else:
    print(f"CSV(s) encontrados: {len(arquivos_csv)}")

    for caminho in arquivos_csv:
        print("\n" + "=" * 70)
        print(f"Arquivo: {caminho.relative_to(RAIZ)}")

        try:
            amostra = pd.read_csv(
                caminho,
                sep=";",
                encoding="latin1",
                nrows=3,
                low_memory=False
            )

            print("\nColunas:")
            print(amostra.columns.tolist())

            print("\nAmostra:")
            print(amostra.head(2).to_string(index=False))

        except Exception as erro:
            print(f"Erro ao ler o arquivo: {erro}")
