"""
dashboard.py - Dashboard Streamlit: crescimento de Jundiaí (SP).
Rodar com:  streamlit run dashboard.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

import api_ibge

st.set_page_config(page_title="Crescimento de Jundiaí", layout="wide")

AZUL, VERDE, LARANJA, ROXO = "#2563eb", "#16a34a", "#f97316", "#7c3aed"
COR_SETOR = {"Agropecuária": VERDE, "Indústria": LARANJA, "Serviços": AZUL, "Administração pública": ROXO}
COR_FONTE = {"Censo": LARANJA, "Estimativa": AZUL}
SETORES = api_ibge.SETORES

st.markdown("""
<style>
h1 { color: #1e3a8a; }
h2, h3 { color: #1d4ed8; }
[data-testid="stMetric"] { background: #f8fafc; padding: 14px 18px; border-radius: 10px; border-left: 6px solid #2563eb; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] { border-left-color: #16a34a; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] { border-left-color: #f97316; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] { border-left-color: #7c3aed; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=24 * 3600, show_spinner="Consultando a API do IBGE...")
def carregar():
    """Consulta a API do IBGE direto (sem arquivo local) e entrega para os gráficos."""
    return api_ibge.obter_tudo()


def br(numero, casas=0):
    """Formata no padrão brasileiro: 1.234,5"""
    return f"{numero:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rgba(cor, transparencia):
    """Converte "#rrggbb" em "rgba(r,g,b,a)" (usado no preenchimento dos gráficos de área)."""
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{transparencia})"


def mostrar(fig, ylabel, fmt=",.0f", altura=360, sufixo="", legenda=False):
    """Aplica o visual padrão e mostra o gráfico."""
    fig.update_layout(template="plotly_white", height=altura, separators=",.", hovermode="x unified",
                      margin=dict(l=10, r=10, t=20, b=10), font=dict(color="#334155"), showlegend=legenda,
                      legend=dict(orientation="h", y=-0.18, x=0, title=None))
    fig.update_xaxes(title=None, showgrid=False)
    fig.update_yaxes(title=ylabel, gridcolor="#e8edf3", tickformat=fmt, ticksuffix=sufixo, zeroline=False)
    st.plotly_chart(fig, width="stretch")


def grafico_area(df, y, cor, ylabel, fmt=",.0f", altura=360, sufixo=""):
    fig = px.area(df, x="ano", y=y)
    fig.update_traces(line_color=cor, line_width=3, fillcolor=rgba(cor, 0.18),
                      mode="lines+markers", marker=dict(size=6, color=cor))
    mostrar(fig, ylabel, fmt, altura, sufixo)


pop, pib = carregar()
ficha = pop.iloc[0]

st.sidebar.header("Filtros")
ano_ini, ano_fim = st.sidebar.slider("Período", int(pop["ano"].min()), int(pop["ano"].max()),
                                     (int(pop["ano"].min()), int(pop["ano"].max())))
fontes = st.sidebar.multiselect("Tipo de dado de população", ["Censo", "Estimativa"], default=["Censo", "Estimativa"],
                                help="Censo: contagem oficial (1970, 1980, 1991, 2000, 2010, 2022). Estimativa: projeção anual do IBGE.")
setores_sel = st.sidebar.multiselect("Setores da economia", SETORES, default=SETORES)
medida = st.sidebar.radio("Setores: medida", ["Valor adicionado (R$ bilhões)", "Participação no valor adicionado (%)"])

d = pop[(pop["ano"] >= ano_ini) & (pop["ano"] <= ano_fim) & (pop["fonte"].isin(fontes))]
if len(d) < 2:
    st.warning("Escolha um período e um tipo de dado com pelo menos dois pontos.")
    st.stop()

st.title("Crescimento de Jundiaí (SP)")
st.markdown("Como a população e a economia de Jundiaí evoluíram ao longo do tempo. "
            "Dados: API do IBGE (Localidades e Agregados/SIDRA).")
st.caption(f"Município: Jundiaí ({ficha['uf']})  |  Região geográfica: {ficha['regiao_geografica']}  |  "
           f"Mesorregião: {ficha['mesorregiao']}  |  Microrregião: {ficha['microrregiao']}  |  "
           f"Região imediata: {ficha['regiao_imediata']}  |  Região intermediária: {ficha['regiao_intermediaria']}")

primeiro, ultimo = d.iloc[0], d.iloc[-1]
anos = ultimo["ano"] - primeiro["ano"]
taxa_ao_ano = ((ultimo["populacao"] / primeiro["populacao"]) ** (1 / anos) - 1) * 100

c1, c2 = st.columns(2)
c1.metric(f"População em {int(ultimo['ano'])}", br(ultimo["populacao"]))
c2.metric("Crescimento da população", f"{br(taxa_ao_ano, 1)}% ao ano",
          f"média entre {int(primeiro['ano'])} e {int(ultimo['ano'])}", delta_color="off")

aba_populacao, aba_economia = st.tabs(["População", "Economia"])

with aba_populacao:
    st.subheader("Evolução da população")
    st.caption("Pontos laranja: Censos. Pontos azuis: estimativas anuais do IBGE.")
    fig = px.area(d, x="ano", y="populacao")
    fig.update_traces(line_color=AZUL, line_width=3, fillcolor=rgba(AZUL, 0.15), hoverinfo="skip")
    pontos = px.scatter(d, x="ano", y="populacao", color="fonte", color_discrete_map=COR_FONTE)
    fig.add_traces(list(pontos.data))
    fig.update_traces(marker=dict(size=9), selector=dict(mode="markers"))
    mostrar(fig, "Habitantes", legenda=True)

with aba_economia:
    st.subheader("Economia de Jundiaí")
    st.caption("Valores a preços correntes (sem descontar a inflação). A série municipal do IBGE começa em 2002.")
    p = pib[(pib["ano"] >= ano_ini) & (pib["ano"] <= ano_fim)]
    total = p[p["categoria"] == "PIB total"].copy()
    if total.empty:
        st.info("Não há dados de PIB para o período selecionado.")
        st.stop()

    total["bilhoes"] = total["valor"] / 1e6
    ano_pib = int(total["ano"].max())
    crescimento_pib = (total["bilhoes"].iloc[-1] / total["bilhoes"].iloc[0] - 1) * 100
    per_capita = p[p["categoria"] == "PIB per capita"].iloc[-1]

    setores = p[p["categoria"].isin(SETORES)].copy()
    setores["bilhoes"] = setores["valor"] / 1e6
    setores["participacao"] = setores["valor"] / setores.groupby("ano")["valor"].transform("sum") * 100
    contagem = setores.groupby("ano")["categoria"].nunique()
    anos_setores = contagem[contagem == len(SETORES)].index.tolist()

    ano_setor, maior_setor, peso = ano_pib, "sem dado", None
    if anos_setores:
        ano_setor = anos_setores[-1]
        valores = setores[setores["ano"] == ano_setor].set_index("categoria")["valor"]
        maior_setor = valores.idxmax()
        peso = valores.max() / valores.sum() * 100

    e1, e2, e3, e4 = st.columns(4)
    e1.metric(f"PIB em {ano_pib}", f"R$ {br(total['bilhoes'].iloc[-1], 1)} bi")
    e2.metric(f"PIB per capita em {int(per_capita['ano'])}", f"R$ {br(per_capita['valor'])}")
    e3.metric("Crescimento do PIB", f"{br(crescimento_pib)}%", f"de {int(total['ano'].min())} a {ano_pib}", delta_color="off")
    e4.metric(f"Maior setor em {ano_setor}", maior_setor,
              f"{br(peso, 1)}% do valor adicionado" if peso else None, delta_color="off")

    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown("**PIB (R$ bilhões)**")
        st.caption("Toda a riqueza produzida no município no ano.")
        grafico_area(total, "bilhoes", ROXO, "R$ bilhões", altura=340)
    with direita:
        if anos_setores:
            ano_pizza = st.selectbox("Ano da composição da economia", anos_setores, index=len(anos_setores) - 1)
            fig = px.pie(setores[setores["ano"] == ano_pizza], names="categoria", values="valor", hole=0.55,
                         color="categoria", color_discrete_map=COR_SETOR)
            fig.update_traces(textinfo="percent")
            fig.update_layout(template="plotly_white", height=300, separators=",.", margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", y=-0.1, x=0, title=None))
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Sem dados de setores no período selecionado.")

    st.subheader("Setores da economia")
    if medida.startswith("Valor"):
        coluna, rotulo, formato, sufixo = "bilhoes", "R$ bilhões", ",.1f", ""
        st.caption("Valor adicionado bruto de cada setor, a preços correntes, em R$ bilhões.")
    else:
        coluna, rotulo, formato, sufixo = "participacao", "% do valor adicionado", ",.0f", "%"
        st.caption("Quanto cada setor representa no valor adicionado total (soma dos quatro setores).")

    colunas = st.columns(2)
    for i, setor in enumerate(s for s in SETORES if s in setores_sel):
        with colunas[i % 2]:
            st.markdown(f"**{setor}**")
            grafico_area(setores[setores["categoria"] == setor], coluna, COR_SETOR[setor], rotulo, formato, 290, sufixo)
