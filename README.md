# Análise Eleitoral 2026 — Presidente

Dashboard interativo para análise dos resultados da eleição presidencial de 2026, utilizando dados do Tribunal Superior Eleitoral (TSE).

O projeto permite explorar os resultados por estado e seção eleitoral, comparar candidatos e visualizar os dados por meio de tabelas e gráficos.

## Tecnologias utilizadas

- Python
- Streamlit
- Pandas
- DuckDB
- Plotly

## Ambiente de desenvolvimento

- Sistema operacional: Windows
- Linguagem: Python
- Editor recomendado: Visual Studio Code (VS Code)

As instruções deste README foram elaboradas para Windows.
Em outros sistemas operacionais, alguns comandos podem ser diferentes.

## 1. Pré-requisitos

Antes de começar, instale:

- [Python](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads/)

## 2. Baixar o projeto

No terminal, execute:

```bash
git clone https://github.com/JheyssonDouglas/analise_eleitoral_2026_presidente.git
cd analise_eleitoral_2026_presidente
```

## 3. Criar o ambiente virtual

No Windows, execute:

```bash
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se estiver usando o Prompt de Comando (CMD), utilize:

```bat
.venv\Scripts\activate.bat
```

## 4. Instalar as dependências

Com o ambiente virtual ativado, execute:

```bash
pip install -r requirements.txt
```

## 5. Baixar e preparar os dados

Os arquivos de dados não estão incluídos neste repositório devido ao seu tamanho. Para executar o projeto, você precisará baixá-los no portal oficial do TSE.

### 5.1. Acessar o portal do TSE

Acesse:

https://dadosabertos.tse.jus.br/dataset/resultados-2026

### 5.2. Baixar os arquivos necessários

Na seção **Dados e recursos**, localize e baixe estes dois recursos:

1. **Presidente - Votação por seção eleitoral - 2026**
2. **Detalhe da apuração por seção eleitoral**

No portal, clique em **Explorar** no recurso correspondente e procure a opção de download do arquivo CSV.

**Importante:** o projeto espera os arquivos nacionais (`BR` e `BRASIL`), e não apenas os arquivos individuais de cada estado.

### 5.3. Organizar os arquivos

Na pasta principal do projeto, crie a seguinte estrutura e coloque cada arquivo no local indicado:

```text
dados/
├── votacao_secao_2026/
│   └── votacao_secao_2026_BR.csv
└── detalhes_votacao_secao_2026/
    └── detalhe_votacao_secao_2026_BRASIL.csv
```

Se os arquivos baixados tiverem nomes diferentes, renomeie-os exatamente como indicado acima.

### 5.4. Processar os dados

Com o ambiente virtual ativado e estando na pasta principal do projeto, execute:

```bash
python src/inspecionar_arquivos.py
python src/processar_dados.py
python src/validar_dados.py
```

O processamento gera os arquivos utilizados pelo dashboard na pasta `saidas/`:

- `votos_presidente_por_secao.csv`
- `resumo_secoes_presidente.csv`

### 5.5. Executar o dashboard

Depois de preparar os dados, inicie a aplicação:

```bash
streamlit run src/app.py
```

O Streamlit informará um endereço local. Abra esse endereço no navegador para acessar o dashboard.

**Observação:** os arquivos de dados e os resultados processados são mantidos localmente e não fazem parte do repositório do GitHub.

## 6. Executar o dashboard

Após preparar os dados, inicie a aplicação:

```bash
streamlit run src/app.py
```

O Streamlit exibirá um endereço local no terminal. Abra esse endereço no navegador para acessar o dashboard.

## Estrutura do projeto

```text
analise_eleitoral_2026_presidente/
├── dados/                  # Arquivos de dados do TSE
├── saidas/                 # Arquivos processados
├── src/
│   ├── app.py              # Dashboard
│   ├── inspecionar_arquivos.py
│   ├── processar_dados.py
│   └── validar_dados.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Fonte dos dados

Os dados utilizados no projeto são provenientes do [Tribunal Superior Eleitoral (TSE)](https://dadosabertos.tse.jus.br/dataset/resultados-2026).

## Observação

Este é um projeto de análise exploratória de dados eleitorais, com finalidade informativa e analítica. Os resultados e as interpretações dependem da qualidade e da atualização dos dados utilizados.