"""Dashboard de crescimento de Jundiaí — versão aprimorada.
Executar: python -m streamlit run dashboard_melhorado.py
Manter api_ibge.py e os CSVs na mesma pasta.
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import api_ibge

st.set_page_config(page_title='Jundiaí | Panorama de Crescimento', page_icon='📊', layout='wide', initial_sidebar_state='expanded')
BASE = Path(__file__).resolve().parent
AZUL, ESCURO, VERDE, LARANJA, ROXO = '#2563eb', '#16345d', '#159b72', '#e98a38', '#7c65c1'
CORES = {'Agropecuária': VERDE, 'Indústria': LARANJA, 'Serviços': AZUL, 'Administração pública': ROXO}
FONTES = {'Censo': LARANJA, 'Estimativa': AZUL}
SETORES = api_ibge.SETORES

st.markdown('''<style>
.stApp {background:#f6f8fc;color:#172b4d}
.block-container {padding-top:2rem;padding-bottom:3rem;max-width:1450px}
h1,h2,h3 {color:#17365c;letter-spacing:-.025em}
h1 {font-size:2.15rem!important}
[data-testid="stMetric"] {background:#fff;border:1px solid #e4eaf2;border-radius:15px;padding:18px 20px;box-shadow:0 4px 15px rgba(30,55,90,.035)}
[data-testid="stMetricLabel"] {color:#64748b}
[data-testid="stMetricValue"] {color:#17365c;font-weight:700}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid #e6ebf2}
[data-testid="stPlotlyChart"] {background:#fff;border:1px solid #e4eaf2;border-radius:15px;padding:8px}
.stTabs [data-baseweb="tab-list"] {gap:12px}
.stTabs [data-baseweb="tab"] {font-weight:600}
</style>''', unsafe_allow_html=True)

def br(v, casas=0):
    if pd.isna(v): return '—'
    return f'{v:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

@st.cache_data(ttl=86400, show_spinner='Carregando dados do IBGE...')
def carregar():
    try:
        pop = pd.read_csv(BASE/'populacao_jundiai.csv', sep=';', encoding='utf-8-sig')
        pib = pd.read_csv(BASE/'pib_jundiai.csv', sep=';', encoding='utf-8-sig')
        if pop.empty or pib.empty or not {'ano','fonte','populacao'}.issubset(pop.columns) or not {'ano','categoria','valor'}.issubset(pib.columns):
            raise ValueError('CSV incompleto')
        origem='CSV locais'
    except (OSError, ValueError, pd.errors.ParserError):
        pop,pib=api_ibge.obter_tudo()
        origem='API do IBGE'
    pop=pop.copy(); pib=pib.copy()
    for df in (pop,pib): df['ano']=pd.to_numeric(df['ano'],errors='coerce')
    pop['populacao']=pd.to_numeric(pop['populacao'],errors='coerce')
    pib['valor']=pd.to_numeric(pib['valor'],errors='coerce')
    pop=pop.dropna(subset=['ano','populacao']).sort_values('ano').drop_duplicates('ano',keep='first')
    pib=pib.dropna(subset=['ano','valor']).sort_values('ano')
    return pop,pib,origem

def estilizar(fig, altura=370, ytitle=None, legenda=False, moeda=False):
    fig.update_layout(template='plotly_white',height=altura,margin=dict(l=20,r=18,t=20,b=28),
        paper_bgcolor='white',plot_bgcolor='white',font=dict(family='Arial',color='#475569'),
        hovermode='x unified',showlegend=legenda,
        legend=dict(orientation='h',y=-.22,x=0,title=None),separators=',.')
    fig.update_xaxes(showgrid=False,title=None,dtick=5)
    fig.update_yaxes(title=ytitle,gridcolor='#edf1f7',zeroline=False)
    if moeda: fig.update_yaxes(tickprefix='R$ ')
    return fig

def baixar(df, nome, titulo):
    st.download_button(titulo,df.to_csv(index=False,sep=';').encode('utf-8-sig'),file_name=nome,mime='text/csv',use_container_width=True)

pop,pib,origem=carregar()
min_ano,max_ano=int(pop.ano.min()),int(pop.ano.max())
st.sidebar.title('Explorar dados')
st.sidebar.caption('Configure o período e as séries exibidas.')
periodo=st.sidebar.slider('Período de análise',min_ano,max_ano,(min_ano,max_ano))
fontes=st.sidebar.multiselect('Origem da população',list(FONTES),default=list(FONTES))
setores_sel=st.sidebar.multiselect('Setores econômicos',SETORES,default=SETORES)
medida=st.sidebar.radio('Visualização dos setores',['Valor adicionado (R$ bilhões)','Participação (%)'])
st.sidebar.divider()
st.sidebar.caption(f'Fonte carregada: **{origem}**')
st.sidebar.caption('Fonte original: IBGE — SIDRA e Localidades.')
st.sidebar.caption('PIB a preços correntes; não ajustado pela inflação.')

st.title('Jundiaí em números')
st.markdown('**Panorama populacional e econômico** · Série histórica do município de Jundiaí, SP')
st.caption(f'Período selecionado: {periodo[0]}–{periodo[1]}  |  Dados: {origem}')

p=pop.loc[pop.ano.between(*periodo)&pop.fonte.isin(fontes)].copy().sort_values('ano')
e=pib.loc[pib.ano.between(*periodo)].copy()
total=e[e.categoria.eq('PIB total')].sort_values('ano').copy()
percap=e[e.categoria.eq('PIB per capita')].sort_values('ano').copy()
setores=e[e.categoria.isin(SETORES)].copy()
setores['bilhoes']=setores.valor/1e6
setores['participacao']=setores.valor/setores.groupby('ano').valor.transform('sum')*100

aba1,aba2,aba3=st.tabs(['👥 População','🏭 Economia','📋 Dados e metodologia'])
with aba1:
    st.subheader('Evolução da população')
    if p.empty:
        st.info('Não há dados populacionais para os filtros selecionados. Selecione ao menos uma origem.')
    else:
        a,b=p.iloc[0],p.iloc[-1]
        delta=int(b.populacao-a.populacao)
        variacao=(b.populacao/a.populacao-1)*100 if a.populacao else None
        intervalo=int(b.ano-a.ano)
        cagr=((b.populacao/a.populacao)**(1/intervalo)-1)*100 if intervalo>0 and a.populacao>0 else None
        k1,k2,k3,k4=st.columns(4)
        k1.metric(f'População · {int(b.ano)}',br(b.populacao))
        k2.metric('Variação absoluta',f'{delta:+,}'.replace(',','.'))
        k3.metric('Variação no período',f'{br(variacao,1)}%' if variacao is not None else '—')
        k4.metric('Crescimento médio anual',f'{br(cagr,2)}%' if cagr is not None else '—')
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=p.ano,y=p.populacao,mode='lines',name='Evolução',line=dict(color=AZUL,width=3),fill='tozeroy',fillcolor='rgba(37,99,235,.09)',hovertemplate='Ano %{x}<br>%{y:,.0f} habitantes<extra></extra>'))
        for fonte,cor in FONTES.items():
            parte=p[p.fonte.eq(fonte)]
            if not parte.empty:
                fig.add_trace(go.Scatter(x=parte.ano,y=parte.populacao,mode='markers',name=fonte,marker=dict(color=cor,size=9,line=dict(color='white',width=1.5)),hovertemplate='Ano %{x}<br>%{y:,.0f} habitantes<extra>'+fonte+'</extra>'))
        st.plotly_chart(estilizar(fig,420,'Habitantes',True),use_container_width=True)
        if intervalo>0:
            st.info(f'**Leitura dos dados:** de {int(a.ano)} a {int(b.ano)}, a população passou de {br(a.populacao)} para {br(b.populacao)} habitantes, uma variação de {br(variacao,1)}% ({br(delta)} pessoas).')
        else: st.caption('Selecione um intervalo com ao menos dois anos disponíveis para calcular o crescimento.')
        st.caption('Os pontos laranja representam censos e os azuis, estimativas. Os intervalos entre observações podem variar.')
        baixar(p,'populacao_filtrada_jundiai.csv','Baixar população filtrada (CSV)')

with aba2:
    st.subheader('Economia do município')
    st.caption('Valores nominais a preços correntes. Comparações entre anos não descontam a inflação.')
    if total.empty:
        st.info('Não existem dados de PIB total para o período selecionado. Experimente anos a partir de 2002.')
    else:
        total['bilhoes']=total.valor/1e6
        ini,fim=total.iloc[0],total.iloc[-1]
        varpib=(fim.valor/ini.valor-1)*100 if len(total)>1 and ini.valor else None
        pc=percap[percap.ano.eq(fim.ano)]
        k1,k2,k3=st.columns(3)
        k1.metric(f'PIB · {int(fim.ano)}',f'R$ {br(fim.bilhoes,2)} bi')
        k2.metric('PIB per capita',f'R$ {br(pc.iloc[-1].valor)}' if not pc.empty else '—')
        k3.metric('Variação nominal do PIB',f'{br(varpib,1)}%' if varpib is not None else '—')
        fig=px.area(total,x='ano',y='bilhoes',markers=True)
        fig.update_traces(line=dict(color=ROXO,width=3),fillcolor='rgba(124,101,193,.12)',marker=dict(size=6))
        st.markdown('#### Evolução do PIB')
        st.plotly_chart(estilizar(fig,370,'R$ bilhões'),use_container_width=True)
        if varpib is not None:
            st.info(f'**Leitura dos dados:** o PIB nominal passou de R$ {br(ini.bilhoes,2)} bilhões ({int(ini.ano)}) para R$ {br(fim.bilhoes,2)} bilhões ({int(fim.ano)}), variação de {br(varpib,1)}%. Esse resultado não representa crescimento real descontada a inflação.')
    st.markdown('#### Composição da economia')
    sel=setores[setores.categoria.isin(setores_sel)].copy()
    anos_completos=sorted(setores.groupby('ano').categoria.nunique().loc[lambda s:s.eq(len(SETORES))].index.astype(int).tolist()) if not setores.empty else []
    anos_disponiveis=sorted(sel.ano.astype(int).unique().tolist()) if not sel.empty else []
    if not anos_disponiveis:
        st.info('Selecione ao menos um setor e um período com dados econômicos.')
    else:
        ano_comp=st.selectbox('Ano de comparação dos setores',anos_disponiveis,index=len(anos_disponiveis)-1)
        s=sel[sel.ano.eq(ano_comp)].copy()
        l,r=st.columns([1,1.5])
        with l:
            donut=px.pie(s,names='categoria',values='valor',hole=.66,color='categoria',color_discrete_map=CORES)
            donut.update_traces(textinfo='percent',hovertemplate='%{label}<br>R$ %{value:,.0f} mil<br>%{percent}<extra></extra>')
            donut.update_layout(template='plotly_white',height=355,margin=dict(l=0,r=0,t=12,b=40),legend=dict(orientation='h',y=-.12,x=0,title=None))
            st.plotly_chart(donut,use_container_width=True)
            if len(setores_sel)<len(SETORES): st.caption('Percentuais do gráfico de rosca recalculados apenas entre os setores selecionados.')
        with r:
            coluna='bilhoes' if medida.startswith('Valor') else 'participacao'
            barras=px.bar(s.sort_values(coluna),x=coluna,y='categoria',orientation='h',color='categoria',color_discrete_map=CORES,text_auto='.1f')
            barras.update_layout(template='plotly_white',height=355,showlegend=False,margin=dict(l=5,r=20,t=12,b=25),xaxis_title='R$ bilhões' if coluna=='bilhoes' else '% do valor adicionado',yaxis_title=None)
            barras.update_xaxes(gridcolor='#edf1f7')
            st.plotly_chart(barras,use_container_width=True)
            if coluna=='participacao': st.caption('Participação calculada sobre os quatro setores originais, mesmo quando apenas alguns estão selecionados.')
        if not s.empty:
            maior=s.loc[s.valor.idxmax()]
            st.info(f'**Leitura dos dados:** entre os setores selecionados, **{maior.categoria}** apresenta o maior valor adicionado em {ano_comp} (R$ {br(maior.bilhoes,2)} bilhões).')
        st.markdown('#### Evolução dos setores selecionados')
        eixo='bilhoes' if medida.startswith('Valor') else 'participacao'
        linhas=px.line(sel.sort_values('ano'),x='ano',y=eixo,color='categoria',color_discrete_map=CORES,markers=True)
        linhas.update_traces(line_width=3)
        st.plotly_chart(estilizar(linhas,380,'R$ bilhões' if eixo=='bilhoes' else '% do valor adicionado',True),use_container_width=True)
        baixar(sel,'setores_filtrados_jundiai.csv','Baixar setores filtrados (CSV)')

with aba3:
    st.subheader('Dados e metodologia')
    st.markdown('**Fontes:** IBGE, APIs de Localidades e de Agregados/SIDRA. O projeto prioriza CSVs locais e recorre à API quando necessário.')
    st.markdown('**População:** censos e estimativas não são observações equivalentes. A taxa média anual utiliza os anos efetivamente disponíveis no filtro.')
    st.markdown('**Economia:** PIB e valor adicionado são apresentados a preços correntes. A participação setorial é calculada sobre a soma dos quatro setores econômicos.')
    st.markdown('**PIB per capita:** o módulo original calcula o indicador com população interpolada nos anos sem observação. Por isso, é uma medida derivada do projeto, não necessariamente a série oficial de PIB per capita.')
    st.markdown('**Cobertura:** a disponibilidade depende dos períodos e categorias presentes na base do IBGE e nos arquivos CSV.')
    with st.expander('Visualizar dados de população'):
        st.dataframe(p,use_container_width=True,hide_index=True)
    with st.expander('Visualizar dados econômicos'):
        st.dataframe(e,use_container_width=True,hide_index=True)
