from itertools import count

import pandas as pd
import plotly.express as px
import streamlit as st

import api_ibge

CHAVES = count()
JUNDIAI = api_ibge.JUNDIAI
st.set_page_config(page_title="Crescimento de Jundiaí", layout="wide")

AZUL, VERDE, LARANJA, ROXO, ROSA, CIANO = "#2563eb", "#16a34a", "#f97316", "#7c3aed", "#e11d48", "#0891b2"
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
[data-testid="stMetric"] {color: #000000 !important;}
[data-testid="stMetricLabel"] {color: #000000 !important;}
[data-testid="stMetricValue"] {color: #000000 !important;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=24 * 3600, show_spinner="Consultando a API do IBGE...")
def carregar():
    return api_ibge.obter_tudo()


def cagr(ini, fim, anos):
    return ((fim / ini) ** (1 / anos) - 1) * 100 if anos > 0 and ini > 0 else float("nan")


def br(n, casas=0):
    return f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def rgba(hex_, alfa):
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alfa})"


def mostrar(fig, ylabel=None, fmt=",.0f", altura=360, sufixo="", legenda=False):
    fig.update_layout(
        template="plotly_white",
        height=altura,
        separators=",.",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=20, b=10),
        font=dict(color="#334155"),
        showlegend=legenda,
        legend=dict(orientation="h", y=-0.18, x=0, title=None)
    )
    fig.update_xaxes(title=None, showgrid=False)
    fig.update_yaxes(
        title=ylabel,
        gridcolor="#e8edf3",
        tickformat=fmt,
        ticksuffix=sufixo,
        zeroline=False
    )
    st.plotly_chart(fig, width="stretch", key=f"grafico_{next(CHAVES)}")


def area(df, y, cor, ylabel, fmt=",.0f", altura=360, sufixo="", marcadores=True):
    fig = px.area(df, x="ano", y=y)
    fig.update_traces(
        line_color=cor,
        line_width=3,
        fillcolor=rgba(cor, 0.18),
        mode="lines+markers" if marcadores else "lines",
        marker=dict(size=6, color=cor)
    )
    mostrar(fig, ylabel, fmt, altura, sufixo)


pop, pib = carregar()
pop = pop[pop["cod"] == JUNDIAI].sort_values("ano")
pib = pib[pib["cod"] == JUNDIAI]


def campo(nome):
    return str(pop[nome].iloc[0]) if nome in pop.columns and pd.notna(pop[nome].iloc[0]) else "-"


st.sidebar.header("Filtros")
a_min, a_max = int(pop["ano"].min()), int(pop["ano"].max())
ano_ini, ano_fim = st.sidebar.slider("Período", a_min, a_max, (a_min, a_max))

fontes = st.sidebar.multiselect(
    "Tipo de dado de população",
    ["Censo", "Estimativa"],
    default=["Censo", "Estimativa"],
    help="Censo: contagem oficial (1970, 1980, 1991, 2000, 2010, 2022). Estimativa: projeção anual do IBGE."
)

setores_sel = st.sidebar.multiselect("Setores da economia", SETORES, default=SETORES)

medida = st.sidebar.radio(
    "Setores: medida",
    ["Valor adicionado (R$ bilhões)", "Participação no valor adicionado (%)"]
)

d = pop[
    (pop["ano"] >= ano_ini) &
    (pop["ano"] <= ano_fim) &
    (pop["fonte"].isin(fontes))
].copy()

if len(d) < 2:
    st.warning("Escolha um período e um tipo de dado com pelo menos dois pontos.")
    st.stop()


st.title("Crescimento de Jundiaí (SP)")

st.markdown(
    "Como a população e a economia de Jundiaí evoluíram ao longo do tempo. "
    "Dados: API do IBGE (Localidades e Agregados/SIDRA)."
)

st.caption(
    f"Município: Jundiaí ({campo('uf')})  |  "
    f"Região geográfica: {campo('regiao_geografica')}  |  "
    f"Mesorregião: {campo('mesorregiao')}  |  "
    f"Microrregião: {campo('microrregiao')}  |  "
    f"Região imediata: {campo('regiao_imediata')}  |  "
    f"Região intermediária: {campo('regiao_intermediaria')}"
)

ini, fim = d.iloc[0], d.iloc[-1]
taxa = cagr(
    ini["populacao"],
    fim["populacao"],
    fim["ano"] - ini["ano"]
)

k1, k2 = st.columns(2)

k1.metric(f"População em {int(fim['ano'])}", br(fim["populacao"]))

k2.metric(
    "Crescimento da população",
    f"{br(taxa, 1)}% ao ano",
    f"média entre {int(ini['ano'])} e {int(fim['ano'])}",
    delta_color="off"
)

aba1, aba2 = st.tabs(["População", "Economia"])


with aba1:
    st.subheader("Evolução da população")
    st.caption("Pontos laranja: Censos. Pontos azuis: estimativas anuais do IBGE.")

    fig = px.area(d, x="ano", y="populacao")

    fig.update_traces(
        line_color=AZUL,
        line_width=3,
        fillcolor=rgba(AZUL, 0.15),
        hoverinfo="skip"
    )

    fig.add_traces(
        list(
            px.scatter(
                d,
                x="ano",
                y="populacao",
                color="fonte",
                color_discrete_map=COR_FONTE
            ).data
        )
    )

    fig.update_traces(
        marker=dict(size=9),
        selector=dict(mode="markers")
    )

    mostrar(fig, "Habitantes", legenda=True)


with aba2:
    st.subheader("Economia de Jundiaí")
    st.caption(
        "Valores a preços correntes (sem descontar a inflação). "
        "A série municipal do IBGE começa em 2002."
    )

    p = pib[
        (pib["ano"] >= ano_ini) &
        (pib["ano"] <= ano_fim)
    ]

    total = p[p["categoria"] == "PIB total"].sort_values("ano").copy()

    if total.empty:
        st.info("Não há dados de PIB para o período selecionado.")

    else:
        total["bilhoes"] = total["valor"] / 1e6

        percap = p[p["categoria"] == "PIB per capita"].sort_values("ano")
        anos_eco = sorted(int(a) for a in total["ano"].unique())
        ano_ref = anos_eco[-1]

        pib_ref = total[total["ano"] == ano_ref]["valor"].iloc[0]
        pc = percap.iloc[-1] if not percap.empty else None

        cresc_pib = (
            (total["bilhoes"].iloc[-1] / total["bilhoes"].iloc[0] - 1) * 100
            if len(total) > 1 else None
        )

        setores_p = p[p["categoria"].isin(SETORES)]
        anos_ok = setores_p.groupby("ano")["categoria"].nunique()

        anos_setores = sorted(
            int(a) for a in anos_ok[anos_ok == len(SETORES)].index
        )

        lider = None

        if anos_setores:
            ano_setor = anos_setores[-1]
            do_ano = setores_p[setores_p["ano"] == ano_setor]
            lider = do_ano.loc[do_ano["valor"].idxmax()]
            peso_lider = lider["valor"] / do_ano["valor"].sum() * 100

        e1, e2, e3, e4 = st.columns(4)

        e1.metric(
            f"PIB em {ano_ref}",
            f"R$ {br(pib_ref / 1e6, 1)} bi"
        )

        e2.metric(
            f"PIB per capita em {int(pc['ano'])}" if pc is not None else "PIB per capita",
            f"R$ {br(pc['valor'])}" if pc is not None else "sem dado"
        )

        e3.metric(
            "Crescimento do PIB",
            f"{br(cresc_pib)}%" if cresc_pib is not None else "sem dado",
            f"de {anos_eco[0]} a {ano_ref}",
            delta_color="off"
        )

        e4.metric(
            f"Maior setor em {ano_setor}" if lider is not None else "Maior setor",
            lider["categoria"] if lider is not None else "sem dado",
            f"{br(peso_lider, 1)}% do valor adicionado" if lider is not None else None,
            delta_color="off"
        )

        g1, g2 = st.columns(2)

        with g1:
            st.markdown("**PIB (R$ bilhões)**")
            st.caption("Toda a riqueza produzida no município no ano.")
            area(total, "bilhoes", ROXO, "R$ bilhões", fmt=",.0f", altura=340)

        with g2:
            if anos_setores:
                ano_pizza = st.selectbox(
                    "Ano da composição da economia",
                    anos_setores,
                    index=len(anos_setores) - 1
                )

                comp = setores_p[setores_p["ano"] == ano_pizza]

                fig = px.pie(
                    comp,
                    names="categoria",
                    values="valor",
                    hole=0.55,
                    color="categoria",
                    color_discrete_map=COR_SETOR
                )

                fig.update_traces(textinfo="percent")

                fig.update_layout(
                    template="plotly_white",
                    height=300,
                    separators=",.",
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", y=-0.1, x=0, title=None)
                )

                st.plotly_chart(
                    fig,
                    width="stretch",
                    key=f"grafico_{next(CHAVES)}"
                )

            else:
                st.caption("Sem dados de setores no período selecionado.")

        st.subheader("Setores da economia")

        if medida.startswith("Valor"):
            st.caption(
                "Valor adicionado bruto de cada setor, a preços correntes, em R$ bilhões."
            )
        else:
            st.caption(
                "Quanto cada setor representa no valor adicionado total (soma dos quatro setores)."
            )

        s = p[p["categoria"].isin(SETORES)].copy()

        s["participacao"] = (
            s["valor"] / s.groupby("ano")["valor"].transform("sum") * 100
        )

        s["bilhoes"] = s["valor"] / 1e6

        coluna, rotulo, fmt, suf = (
            ("bilhoes", "R$ bilhões", ",.1f", "")
            if medida.startswith("Valor")
            else ("participacao", "% do valor adicionado", ",.0f", "%")
        )

        cols = st.columns(2)

        for i, setor in enumerate(x for x in SETORES if x in setores_sel):
            with cols[i % 2]:
                st.markdown(f"**{setor}**")

                ds = s[s["categoria"] == setor].sort_values("ano")

                if ds.empty:
                    st.caption("Sem dados.")
                else:
                    area(
                        ds,
                        coluna,
                        COR_SETOR[setor],
                        rotulo,
                        fmt=fmt,
                        altura=290,
                        sufixo=suf
                    )
