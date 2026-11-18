# Dashboard: Crescimento de Jundiaí (SP)

Dashboard em Streamlit que analisa o crescimento **populacional** e **econômico** de Jundiaí (SP), partindo do interesse dos membros do grupo em analisar as mudanças da cidade.

Tecnologias: **Python**, **Streamlit**, **Pandas**, **Requests** e **Plotly Express**.

Fonte dos dados: [API de Localidades e Agregados (SIDRA) do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades).

## Como os dados são carregados

O dashboard segue esta ordem:

1. Procura os arquivos `populacao_jundiai.csv` e `pib_jundiai.csv` na pasta do projeto.
2. Se não encontrar (ou se estiverem vazios/inválidos), busca direto na API do IBGE.

A barra lateral mostra a fonte usada ("CSV locais" ou "API do IBGE"). Para atualizar os CSVs com dados novos, rode `python api_ibge.py` (passo 5).

## Estrutura do projeto

```
dashboard-crescimento-jundiai/
├── dashboard.py          # aplicação Streamlit
├── api_ibge.py           # acesso e tratamento dos dados da API do IBGE (gera os CSVs)
├── populacao_jundiai.csv # dados de população (gerado)
├── pib_jundiai.csv       # dados de PIB e setores (gerado)
├── requirements.txt      # dependências
└── imagens/              # capturas de tela usadas neste README
```

## Pré-requisitos

- **Python 3.10 ou superior** (testado com 3.12). Verifique com `python --version`.
- **pip** (já vem com o Python).
- Conexão com a internet (apenas se os CSVs não existirem, ou para atualizá-los).
- Opcional: **Git**, para clonar o repositório.

## Passo a passo

### 1. Obter o projeto

Com Git:

```bash
git clone <url-do-repositorio>
cd dashboard-crescimento-jundiai
```

Ou baixe o `.zip`, extraia e entre na pasta `dashboard-crescimento-jundiai` pelo terminal.

### 2. Criar o ambiente virtual (venv)

**Windows (PowerShell ou CMD):**

```bash
python -m venv venv
```

**Linux / macOS:**

```bash
python3 -m venv venv
```

### 3. Ativar o ambiente virtual

**Windows (PowerShell):**

```powershell
venv\Scripts\Activate.ps1
```

Se aparecer erro de política de execução, rode antes:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

**Windows (CMD):**

```bat
venv\Scripts\activate.bat
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

Quando ativo, o terminal mostra `(venv)` no início da linha.

### 4. Instalar as dependências

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. (Opcional) Gerar ou atualizar os CSVs

Se os CSVs já estão na pasta, pule este passo. Para gerá-los (ou atualizá-los) a partir da API do IBGE:

```bash
python api_ibge.py
```

Serão criados `populacao_jundiai.csv` e `pib_jundiai.csv`.

### 6. Rodar o dashboard

```bash
streamlit run dashboard.py
```