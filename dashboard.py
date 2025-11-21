import streamlit as st
import pandas as pd
import plotly.express as px
import warnings
import datetime
import logging
import sys
import json
from io import BytesIO


# --- CSS PARA REDUZIR ESPAÇAMENTO ENTRE LINHAS ---
# --- CSS PERSONALIZADO (NO INÍCIO DO dashboard.py) ---
st.markdown(
    """
    <style>
    /* 1. Redução de Espaçamento Geral */
    .st-emotion-cache-18ni7ap, .st-emotion-cache-1y4pm5r, .st-emotion-cache-7ym5gk {
        padding-top: 0px;
        padding-bottom: 0px;
        margin-top: 0px;
        margin-bottom: 0px;
    }
    p {
        margin: 0px;
        padding: 0px;
    }
    
    /* 2. REDUÇÃO DO TAMANHO DO BOTÃO (NOVO) */
    /* Atinge especificamente os botões dentro das colunas */
    [data-testid="stColumn"] button {
        height: 3px; /* Altura fixa do botão */
        line-height: 3px; /* Ajusta a altura da linha do texto dentro do botão */
        padding: 0px 3px !important; /* Reduz o preenchimento horizontal e vertical */
        font-size: 3px; /* Reduz o tamanho da fonte (se precisar) */
    }
    </style>
    """,
    unsafe_allow_html=True
)
# ----------------------------------------------------------------

def to_excel(df: pd.DataFrame):
    """Converte o DataFrame para o formato Excel (xlsx) em memória."""
    output = BytesIO()
    # Usamos o Pandas ExcelWriter para criar o arquivo xlsx
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # AQUI VOCÊ EXPORTA O DATAFRAME COM DADOS NUMÉRICOS (df_final_raw)
        df.to_excel(writer, index=False, sheet_name='Análise de Queda')
    
    # Retorna o arquivo binário
    return output.getvalue()


OBS_FILE = 'observacoes_clientes.json'

#Arquivo de observações dos clientes
def carregar_observacoes():
    """Carrega as observações do arquivo JSON, ou retorna um dicionário vazio se não existir."""
    try:
        with open(OBS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

#Arquivo de observações dos clientes
def salvar_observacoes(observacoes):
    """Salva o dicionário de observações no arquivo JSON."""
    with open(OBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(observacoes, f, indent=4, ensure_ascii=False)

# Configuração básica do logging para o console (stdout)
logging.basicConfig(
    level=logging.INFO,  # Define o nível mínimo de log a ser exibido
    format='%(asctime)s - %(levelname)s - %(message)s', # Define o formato da mensagem
    handlers=[logging.StreamHandler(sys.stdout)] # Direciona a saída para o console
)

logger = logging.getLogger(__name__)
logger.info(f"Usuario ativo {st.context.ip_address}")

# Ignorar avisos que podem poluir o dashboard
warnings.filterwarnings('ignore')

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Vendas",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard de Vendas")

# --- Função de Carregamento de Dados (com Cache e Limpeza) ---
#@st.cache_data
@st.cache_resource
def carregar_dados(caminho_arquivo):
    """
    Carrega o arquivo CSV, trata a formatação de números e processa o novo campo 'MESANO' 
    para gerar as colunas temporais necessárias.
    """
    try:
        # Tenta ler o CSV (mantendo o delimiter=',' como você usou)
        #df = pd.read_csv(caminho_arquivo, delimiter=',') 
        df = pd.read_csv(caminho_arquivo, sep=',') #Para tenttar ler o arquivo no googledrive
        
        # 1. LIMPEZA DE COLUNAS: Remove espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip() 

        # 2. VERIFICAÇÃO INICIAL
        if df.empty:
            st.error("O arquivo CSV foi lido, mas não contém dados.")
            return None

        # --- Tratamento de Colunas Numéricas ---
        colunas_numericas = ['FATURA_KG', 'FATURA_RS', 'PRECO_MEDIO', 'BONIF_KG']
        
        for col in colunas_numericas:
            if col in df.columns:
                # Trata formato brasileiro (milhar: ponto, decimal: vírgula)
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                st.warning(f"A coluna '{col}' não foi encontrada no arquivo. Verifique o cabeçalho.")
                return None 
        
        # --- NOVO: Tratamento de MESANO (11/2025) ---
        if 'MESANO' not in df.columns:
            # Caso o arquivo ainda tenha a estrutura antiga (MÊS e ANO), use a lógica anterior
            if 'MÊS' in df.columns and 'ANO' in df.columns:
                 st.warning("Usando a estrutura antiga (MÊS/ANO). Verifique se o campo 'MESANO' foi adicionado corretamente.")
            else:
                st.error("O arquivo não contém o campo 'MESANO', 'MÊS', ou 'ANO'. O processamento de datas não pode continuar.")
                return None
        
        # 1. Converte MESANO para o formato de data (DD/MM/AAAA -> 01/MM/AAAA)
        # O formato de entrada é MM/YYYY, então forçamos o dia '01/'
        df['DATA_REF'] = pd.to_datetime('01/' + df['MESANO'], format='%d/%m/%Y', errors='coerce')

        # 2. Cria as colunas MÊS e ANO a partir do DATA_REF para os filtros (em português)
        df['ANO'] = df['DATA_REF'].dt.strftime('%Y')
        df['MÊS'] = df['DATA_REF'].dt.strftime('%B').str.lower().str.strip()

        # Dicionário para garantir que os nomes dos meses estejam em português
        traducao_mes = {
            'january': 'janeiro', 'february': 'fevereiro', 'march': 'março', 
            'april': 'abril', 'may': 'maio', 'june': 'junho',
            'july': 'julho', 'august': 'agosto', 'september': 'setembro', 
            'october': 'outubro', 'november': 'novembro', 'december': 'dezembro'
        }
        df['MÊS'] = df['MÊS'].replace(traducao_mes, regex=True)

        # --- Tratamento de Texto (Limpeza de espaços) ---
        # Não precisamos mais do df['MÊS'].str.strip() pois foi recriado
        df['FAMILIA'] = df['FAMILIA'].str.strip()
        df['UF'] = df['UF'].str.strip()
        df['COORDENADOR'] = df['COORDENADOR'].str.strip()
        df['REPRESENTANTE'] = df['REPRESENTANTE'].str.strip() 

        # Remove linhas que falharam na conversão de data ou que têm valores nulos essenciais
        df = df.dropna(subset=['DATA_REF', 'FATURA_RS', 'FATURA_KG'])
        
        return df
    
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
        st.info("Por favor, certifique-se de que o arquivo .csv está na mesma pasta que o script Python.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado durante o processamento de dados: {e}")
        return None


# --- Carregar os Dados ---
#ARQUIVO = 'Dados.csv'
ARQUIVO = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR78roOtheg4zIdS2FZb7WvF8UAb64nuH3nxbn8fJWEg-ZPsuy18m_AZCRfU2ST3-jJOurK0DmSo5PA/pub?output=csv' #Para tentar ler o arquivo no googledrive
           
df = carregar_dados(ARQUIVO)

if df is None or df.empty:
    st.info("A execução do dashboard foi interrompida devido a erros ou falta de dados.")
    st.stop() 

# --- Dicionário de meses para ordenação correta (fora da função)
mes_map_ordem = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}


if st.sidebar.button("Recarregar Dados"):
    # Esta função Streamlit limpa programaticamente todos os caches
    st.cache_resource.clear() 
    # Recarrega a página para buscar os novos dados
    st.rerun()

st.sidebar.markdown("---")

# --- Barra Lateral de Filtros ---
st.sidebar.header("Filtros Interativos")

# --- Função de Callback para o Checkbox ---
def toggle_all(key_col, df_data, mes_ordenacao=False):
    """Função chamada quando o checkbox 'Selecionar Todos' é clicado."""
    opcoes_disponiveis = df_data[key_col].unique().tolist()
    
    if mes_ordenacao:
        opcoes_disponiveis = sorted(opcoes_disponiveis, key=lambda m: mes_map_ordem.get(m.lower().strip(), 0))
    else:
        opcoes_disponiveis = sorted(opcoes_disponiveis)
    
    # Se o checkbox for True, define a lista de seleção como todas as opções.
    # Se for False, define a lista de seleção como vazia.
    if st.session_state[f"check_{key_col}"]:
        st.session_state[f"filter_{key_col}"] = opcoes_disponiveis
    else:
        st.session_state[f"filter_{key_col}"] = []


# --- Lógica de Inicialização do Session State ---
# Devemos inicializar o st.session_state para as chaves do multiselect na primeira execução.
# Se o estado não existir, inicializamos com TODAS as opções.
def initialize_filter_state(key_col, df_data, mes_ordenacao=False):
    if f"filter_{key_col}" not in st.session_state:
        opcoes_disponiveis = df_data[key_col].unique().tolist()
        if mes_ordenacao:
            opcoes_disponiveis = sorted(opcoes_disponiveis, key=lambda m: mes_map_ordem.get(m.lower().strip(), 0))
        else:
            opcoes_disponiveis = sorted(opcoes_disponiveis)
        
        # Inicializa com todas as opções selecionadas
        st.session_state[f"filter_{key_col}"] = opcoes_disponiveis
        # Inicializa o checkbox como marcado
        st.session_state[f"check_{key_col}"] = True

# --- Geração dos Filtros ---

# FILTRO: ANO
initialize_filter_state('ANO', df)
st.sidebar.checkbox(
    "Selecionar todos (Ano)", 
    value=st.session_state["check_ANO"], 
    key="check_ANO",
    on_change=toggle_all, 
    args=('ANO', df, False)
)
ano = st.sidebar.multiselect(
    "Ano:",
    options=sorted(df['ANO'].unique()),
    key='filter_ANO' # O valor deste multiselect é controlado pelo session_state e pelo checkbox
)


# FILTRO: MÊS
initialize_filter_state('MÊS', df, mes_ordenacao=True)
st.sidebar.checkbox(
    "Selecionar todos (Mês)", 
    value=st.session_state["check_MÊS"], 
    key="check_MÊS",
    on_change=toggle_all, 
    args=('MÊS', df, True)
)
meses_disponiveis = sorted(df['MÊS'].unique(), key=lambda m: mes_map_ordem.get(m.lower().strip(), 0))
mes = st.sidebar.multiselect(
    "Mês:",
    options=meses_disponiveis,
    key='filter_MÊS'
)


# FILTRO: REPRESENTANTE
initialize_filter_state('REPRESENTANTE', df)
st.sidebar.checkbox(
    "Selecionar todos (Representante)", 
    value=st.session_state["check_REPRESENTANTE"], 
    key="check_REPRESENTANTE",
    on_change=toggle_all, 
    args=('REPRESENTANTE', df, False)
)
representante = st.sidebar.multiselect(
    "Representante:",
    options=sorted(df['REPRESENTANTE'].unique()),
    key='filter_REPRESENTANTE'
)


# FILTRO: FAMÍLIA
initialize_filter_state('FAMILIA', df)
st.sidebar.checkbox(
    "Selecionar todos (Família)", 
    value=st.session_state["check_FAMILIA"], 
    key="check_FAMILIA",
    on_change=toggle_all, 
    args=('FAMILIA', df, False)
)
familia = st.sidebar.multiselect(
    "Família:",
    options=sorted(df['FAMILIA'].unique()),
    key='filter_FAMILIA'
)


# FILTRO: UF
initialize_filter_state('UF', df)
st.sidebar.checkbox(
    "Selecionar todos (UF)", 
    value=st.session_state["check_UF"], 
    key="check_UF",
    on_change=toggle_all, 
    args=('UF', df, False)
)
uf = st.sidebar.multiselect(
    "UF:",
    options=sorted(df['UF'].unique()),
    key='filter_UF'
)


# FILTRO: COORDENADOR
initialize_filter_state('COORDENADOR', df)
st.sidebar.checkbox(
    "Selecionar todos (Coordenador)", 
    value=st.session_state["check_COORDENADOR"], 
    key="check_COORDENADOR",
    on_change=toggle_all, 
    args=('COORDENADOR', df, False)
)
coordenador = st.sidebar.multiselect(
    "Coordenador:",
    options=sorted(df['COORDENADOR'].unique()),
    key='filter_COORDENADOR'
)

# FILTRO: CLIENTE (NOME)
initialize_filter_state('NOME', df) # 'NOME' é o nome da coluna no seu CSV
st.sidebar.checkbox(
    "Selecionar todos (Cliente)", 
    value=st.session_state["check_NOME"], 
    key="check_NOME",
    on_change=toggle_all, 
    args=('NOME', df, False)
)
cliente = st.sidebar.multiselect(
    "Cliente:",
    options=sorted(df['NOME'].unique()),
    key='filter_NOME'
)

# FILTRO: PRODUTO
initialize_filter_state('PRODUTO', df)
st.sidebar.checkbox(
    "Selecionar todos (Produto)", 
    value=st.session_state["check_PRODUTO"], 
    key="check_PRODUTO",
    on_change=toggle_all, 
    args=('PRODUTO', df, False)
)
produto = st.sidebar.multiselect(
    "Produto:",
    options=sorted(df['PRODUTO'].unique()),
    key='filter_PRODUTO'
)



# --- Filtrar o DataFrame com base nas seleções ---
# Agora, as variáveis de filtro (ano, mes, etc.) são lidas diretamente do session_state
# A variável 'ano' no código a seguir deve ser o valor de st.session_state['filter_ANO']
# O multiselect key='filter_ANO' já retorna o valor para a variável 'ano' automaticamente.
# No entanto, se o usuário não selecionar nada, o multiselect retorna uma lista vazia,
# que é o que precisamos para o isin.

# Lemos as variáveis de filtro do multiselect (que por sua vez, são controladas pelo session_state)
ano = st.session_state['filter_ANO']
mes = st.session_state['filter_MÊS']
representante = st.session_state['filter_REPRESENTANTE']
familia = st.session_state['filter_FAMILIA']
uf = st.session_state['filter_UF']
coordenador = st.session_state['filter_COORDENADOR']
cliente = st.session_state['filter_NOME']
produto = st.session_state['filter_PRODUTO']


# (O restante do código, incluindo a filtragem do DataFrame, continua)
# ----------------------------------------------------------------------------------

# Se não houver nada selecionado em algum filtro (lista vazia), o isin([])
# retornará um DataFrame vazio, que será tratado pelo if df_filtrado.empty.
df_filtrado = df[
    (df['ANO'].isin(ano)) &
    (df['MÊS'].isin(mes)) &
    (df['REPRESENTANTE'].isin(representante)) &
    (df['FAMILIA'].isin(familia)) &
    (df['UF'].isin(uf)) &
    (df['COORDENADOR'].isin(coordenador)) &
    (df['NOME'].isin(cliente)) &
    (df['PRODUTO'].isin(produto))
]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()
    
    
# O restante do código (KPIs e Gráficos) continua aqui...
# -------------------------------------------------------------


# --- Exibir KPIs (Indicadores-Chave) ---
st.subheader("Indicadores-Chave de Performance")

# Calcular KPIs
total_rs = df_filtrado['FATURA_RS'].sum()
total_kg = df_filtrado['FATURA_KG'].sum()
preco_medio = (total_rs / total_kg) if total_kg > 0 else 0
total_bonif_kg = df_filtrado['BONIF_KG'].sum()
taxa_bonif = (total_bonif_kg / total_kg * 100) if total_kg > 0 else 0
clientes_unicos = df_filtrado['CLIENTE'].nunique()

# Função auxiliar para formatar em pt-BR (R$ 1.234,56)
def formatar_br(valor, is_currency=True):
    try:
        if is_currency:
            return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        else:
            return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except:
        return f"{valor}"

col1, col2, col3 = st.columns(3)
col1.metric("Venda Total (R$)", formatar_br(total_rs))
col2.metric("Volume Total (Kg)", f"{formatar_br(total_kg, is_currency=False)} Kg")
col3.metric("Clientes Únicos", f"{clientes_unicos}")

col4, col5, col6 = st.columns(3)
col4.metric("Preço Médio (R$/Kg)", formatar_br(preco_medio))
col5.metric("Bonificação (Kg)", f"{formatar_br(total_bonif_kg, is_currency=False)} Kg")
col6.metric("Taxa de Bonificação (%)", f"{formatar_br(taxa_bonif, is_currency=False)}%")

st.markdown("---") 
st.subheader("Análises Gráficas")

# --- GRÁFICOS (Layout) ---
col_graf1, col_graf2 = st.columns(2)
col_graf3, col_graf4 = st.columns(2)


# Gráfico 1: Evolução do Faturamento Mensal (Linha)
with col_graf1:
    # 1. Agrupar os dados filtrados (Não precisamos de reindexação se todos os meses existirem)
    df_evolucao = df_filtrado.groupby('DATA_REF')['FATURA_RS'].sum().reset_index()

    # 2. Criar o gráfico
    fig_evolucao = px.line(
        df_evolucao.sort_values(by='DATA_REF'), 
        x='DATA_REF', 
        y='FATURA_RS', 
        title="1. Evolução das vendas Mensal (R$) - Meses Contínuos",
        labels={'DATA_REF': 'Data', 'FATURA_RS': 'Faturamento (R$)'}
    )
    
    # 3. Configuração para forçar a exibição de todos os meses no eixo X
    fig_evolucao.update_xaxes(
        # Formato: Exibe o mês abreviado e o ano (Jan 2025)
        tickformat="%b %Y", 
        # Força um 'tick' (rótulo) a cada 1 mês ('M1')
        dtick="M1",
        # Configura para exibir todas as datas disponíveis, se possível, sem otimização
        type='date' 
    )
    
    #st.plotly_chart(fig_evolucao, width='stretch')
    #st.plotly_chart(fig_evolucao, width='stretch', config={})
    st.plotly_chart(fig_evolucao, config={})

# Gráfico 2: NOVO - Comparação Anual (YoY)
with col_graf2:
    # Agrupa por Mês e Ano para a comparação
    df_yoy = df_filtrado.groupby(['MÊS', 'ANO'])['FATURA_RS'].sum().reset_index()
    
    # Ordena os meses para o gráfico de barra
    df_yoy['MÊS_ORDEM'] = df_yoy['MÊS'].str.lower().map(mes_map_ordem)
    df_yoy = df_yoy.sort_values(by=['MÊS_ORDEM', 'ANO'])
    
    fig_yoy = px.bar(
        df_yoy, 
        x='MÊS', 
        y='FATURA_RS', 
        color='ANO', 
        barmode='stack', # Barras lado a lado
        title="2. Comparação Anual (YoY) - Vendas por Mês",
        labels={'MÊS': 'Mês', 'FATURA_RS': 'Faturamento (R$)', 'ANO': 'Ano'}
    )
    #st.plotly_chart(fig_yoy, width='stretch' , config={})
    st.plotly_chart(fig_yoy, config={})


# Gráfico 3: Top 10 Representantes (R$) por Ano
with col_graf3:
    # 1. Calcular o Faturamento TOTAL de cada representante no período filtrado para determinar o TOP 10
    # Usamos REPRESENTANTE, que é a coluna que você usa para filtrar
    top_10_reps = df_filtrado.groupby('REPRESENTANTE')['FATURA_RS'].sum().nlargest(15).index
    
    # 2. Filtrar o DataFrame apenas para esses Top 10 Representantes
    df_top_10_reps = df_filtrado[df_filtrado['REPRESENTANTE'].isin(top_10_reps)]
    
    # 3. Agrupar os dados dos Top 10 por Representante e por Ano
    df_reps_ano = df_top_10_reps.groupby(['REPRESENTANTE', 'ANO'])['FATURA_RS'].sum().reset_index()
    
    # 4. Criar o gráfico de barras, usando 'ANO' como cor para separação
    fig_top_reps = px.bar(
        df_reps_ano, 
        x='FATURA_RS', 
        y='REPRESENTANTE', 
        color='ANO',  # NOVO: Separa por ano
        barmode='stack', # MODO: Barras lado a lado
        orientation='h',
        title="3. Top 15 Representantes (R$) Comparado por Ano", 
        labels={'REPRESENTANTE': 'Representante', 'FATURA_RS': 'Faturamento (R$)', 'ANO': 'Ano'}
    )
    
    # Ajusta a ordem para que os representantes fiquem ordenados pelo total geral
    rep_ordem = df_filtrado.groupby('REPRESENTANTE')['FATURA_RS'].sum().sort_values(ascending=True).index.tolist()
    fig_top_reps.update_layout(yaxis={'categoryorder':'array', 'categoryarray':rep_ordem})

    #st.plotly_chart(fig_top_reps, width='stretch' , config={})
    st.plotly_chart(fig_top_reps, config={})

# Gráfico 4: Top 15 Clientes (R$) por Ano
with col_graf4:
    # 1. Calcular o Faturamento TOTAL de cada cliente no período filtrado para determinar o TOP 10
    top_10_nomes = df_filtrado.groupby('NOME')['FATURA_RS'].sum().nlargest(15).index
    
    # 2. Filtrar o DataFrame apenas para esses Top 10 Clientes
    df_top_10 = df_filtrado[df_filtrado['NOME'].isin(top_10_nomes)]
    
    # 3. Agrupar os dados dos Top 10 por Cliente e por Ano
    df_clientes_ano = df_top_10.groupby(['NOME', 'ANO'])['FATURA_RS'].sum().reset_index()
    
    # 4. Criar o gráfico de barras, usando 'ANO' como cor para separação
    fig_top_clientes = px.bar(
        df_clientes_ano, 
        x='FATURA_RS', 
        y='NOME', 
        color='ANO',  # COR: Separa por ano
        barmode='stack', # MODO: Barras lado a lado (em vez de empilhadas)
        orientation='h',
        title="4. Top 15 Clientes (R$) Comparado por Ano", 
        labels={'NOME': 'Cliente', 'FATURA_RS': 'Faturamento (R$)', 'ANO': 'Ano'}
    )
    
    # Ajusta a ordem para que os clientes fiquem ordenados pelo total geral, do menor para o maior
    # (ascending=True para o Plotly exibir de baixo para cima, do menor ao maior total)
    nome_ordem = df_filtrado.groupby('NOME')['FATURA_RS'].sum().sort_values(ascending=True).index.tolist()
    fig_top_clientes.update_layout(yaxis={'categoryorder':'array', 'categoryarray':nome_ordem})

    #st.plotly_chart(fig_top_clientes, width='stretch', config={})
    st.plotly_chart(fig_top_clientes, config={})

col_graf5, col_graf6 = st.columns(2)

# Gráfico 5: Composição do Faturamento por Família (Pizza)
with col_graf5:
    df_familia = df_filtrado.groupby('FAMILIA')['FATURA_RS'].sum().reset_index()
    fig_familia = px.pie(
        df_familia, 
        values='FATURA_RS', 
        names='FAMILIA', 
        title="5. Composição das vendsa por Família (R$)"
    )
    #st.plotly_chart(fig_familia, width='stretch' , config={})
    st.plotly_chart(fig_familia, config={})

# Gráfico 6: Faturamento por UF (Comparado por Ano)
with col_graf6:
    # Agrupa os dados por UF e por ANO
    df_uf_ano = df_filtrado.groupby(['UF', 'ANO'])['FATURA_RS'].sum().reset_index()
    df_uf_ano.sort_values(by='FATURA_RS', ascending=False, inplace=True)
    
    fig_uf = px.bar(
        #df_uf_ano.sort_values(by='FATURA_RS', ascending=False),
        df_uf_ano, 
        x='UF', 
        y='FATURA_RS', 
        color='ANO', # NOVO: Separa por ano
        barmode='stack', # MODO: Barras lado a lado
        title="6. Vendas por UF (R$) Comparado por Ano",
        labels={'UF': 'Estado', 'FATURA_RS': 'Venda (R$)', 'ANO': 'Ano'}
    )
    # Garante que o eixo X (UF) não seja cortado se tiver muitas UFs
    fig_uf.update_xaxes(tickangle=45) 

    #st.plotly_chart(fig_uf, width='stretch', config={})
    st.plotly_chart(fig_uf, config={})

    # --- Adicionar uma nova linha de gráficos para o Gráfico 7 (Top Produtos) ---

st.markdown("---") 
st.subheader("Análise de Produtos")

col_graf7, col_graf8 = st.columns([1, 1]) # O gráfico 7 usará a primeira coluna (col_graf7), a segunda será vazia ou para futuro uso


# --- Análise de Produtos: Gráfico 7 (Pizza) e Gráfico 8 (Preço Médio) ---
#st.markdown("---") 
#st.subheader("Análise de Produtos")    

# 1. Preparação dos Dados para o TOP 15 (Comum aos dois gráficos)
# Agrupa os dados por produto e calcula o Faturamento Total (R$) e Volume Total (KG)
df_produtos_agregado = df_filtrado.groupby(['PRODUTO', 'DESCRICAO']).agg(
    FATURA_RS=('FATURA_RS', 'sum'),
    FATURA_KG=('FATURA_KG', 'sum')
).reset_index()

# Seleciona os 15 produtos com maior faturamento (FATURA_RS)
df_top_15 = df_produtos_agregado.nlargest(15, 'FATURA_RS')

# Adiciona a coluna PRODUTO_COMPLETO
df_top_15['PRODUTO_COMPLETO'] = df_top_15['PRODUTO'] + ' - ' + df_top_15['DESCRICAO']

# Calcula o Preço Médio (R$/Kg) SOMA(R$)/SOMA(KG)
# Onde FATURA_KG é zero, preenche o preço médio com 0 para evitar divisão por zero
df_top_15['PRECO_MEDIO_CALCULADO'] = df_top_15.apply(
    lambda row: row['FATURA_RS'] / row['FATURA_KG'] if row['FATURA_KG'] > 0 else 0,
    axis=1
)


# Criação das colunas para os gráficos 7 e 8
col_graf7, col_graf8 = st.columns(2) 


# --- GRÁFICO 7: Top 15 Produtos (R$) - PIZZA ---
with col_graf7:
    
    # 4. Criar o gráfico de pizza (usando df_top_15)
    fig_top_produtos = px.pie(
        df_top_15, 
        values='FATURA_RS', 
        names='PRODUTO_COMPLETO', 
        title="7. Top 15 Produtos Mais Vendidos (R$)",
        hole=.3, 
        hover_data=['PRODUTO', 'DESCRICAO'],
    )
    
    fig_top_produtos.update_traces(textposition='inside', textinfo='percent+label')
    fig_top_produtos.update_layout(showlegend=True)

    #st.plotly_chart(fig_top_produtos, width='stretch', config={})
    st.plotly_chart(fig_top_produtos, config={})


# --- GRÁFICO 8: Top 15 Produtos - PREÇO MÉDIO CALCULADO ---
with col_graf8:
    # Ordena os produtos pelo Preço Médio Calculado (do menor para o maior)
    df_pmv_ordenado = df_top_15.sort_values(by='PRECO_MEDIO_CALCULADO', ascending=True)

    fig_pmv = px.bar(
        df_pmv_ordenado, 
        x='PRECO_MEDIO_CALCULADO', 
        y='PRODUTO_COMPLETO', 
        orientation='h',
        title="8. Preço Médio Calculado (R$/Kg) - Top 15 Produtos",
        labels={'PRODUTO_COMPLETO': 'Produto', 'PRECO_MEDIO_CALCULADO': 'Preço Médio (R$/Kg)'},
        text='PRECO_MEDIO_CALCULADO'  # Define a coluna que será usada como texto
    )
    
    # 1. Formata os rótulos de texto na barra para aparecer como R$ X,XX
    fig_pmv.update_traces(
        # textposition='auto', # Garante que o texto se ajuste automaticamente
        texttemplate='R$ %{text:.2f}', # Adiciona R$ e limita a 2 casas decimais
        insidetextanchor='start', # Coloca o texto no início da barra
        textfont_size=12 # Opcional: Ajusta o tamanho da fonte
    )
    
    # 2. Formata o eixo X como moeda (R$)
    fig_pmv.update_xaxes(tickprefix='R$ ')

    #st.plotly_chart(fig_pmv, width='stretch', config={})
    st.plotly_chart(fig_pmv, config={})

    # --- Tabela de Clientes Inativos (Análise de Churn/Risco) ---
st.markdown("---")
st.subheader("Análise de Clientes Inativos (Risco de Churn)")

# --- Lógica de Data Dinâmica ---
data_hoje = datetime.datetime.now()
DATA_LIMITE = pd.to_datetime(data_hoje.strftime('%Y-%m-01'))
mes_referencia = data_hoje.strftime('%B %Y').capitalize() 

st.caption(f"Clientes cuja última compra foi **anterior** ao mês de referência: {mes_referencia} (Baseado nos filtros aplicados).")

# 1. Fonte de dados: Usamos o DF FILTRADO para refletir as seleções do usuário
# Isso garante que se o usuário filtrar por CE, só veremos clientes de CE.
df_base_tabela = df_filtrado.copy()

# 2. Encontrar a data da última compra (DATA_REF) para cada cliente
# A última compra é determinada DENTRO DO CONJUNTO DE DADOS FILTRADO
df_ultima_compra = df_base_tabela.groupby('NOME')['DATA_REF'].max().reset_index()
df_ultima_compra.rename(columns={'DATA_REF': 'DATA_ULTIMA_COMPRA'}, inplace=True)

# 3. Filtrar inativos: Última compra anterior ao mês de referência (DINÂMICO)
df_inativos = df_ultima_compra[df_ultima_compra['DATA_ULTIMA_COMPRA'] < DATA_LIMITE]

if not df_inativos.empty:
    
    # 4. Trazer o nome do Representante e UF
    # Usamos o df_filtrado (que já está reduzido) para pegar as colunas, eliminando duplicatas
    df_caracteristicas = df_filtrado[['NOME', 'REPRESENTANTE', 'UF']].drop_duplicates(subset=['NOME'])
    
    df_tabela_inativos = pd.merge(
        df_inativos, 
        df_caracteristicas, 
        on='NOME', 
        how='left'
    )
    
    # 5. Cria a coluna 'Mês da Última Compra' formatada para exibição
    df_tabela_inativos['MÊS_ULTIMA_COMPRA'] = df_tabela_inativos['DATA_ULTIMA_COMPRA'].dt.strftime('%b/%Y')

    # 6. Ordenar: DATA_ULTIMA_COMPRA (desc.) e REPRESENTANTE (cresc.)
    df_tabela_inativos.sort_values(
        by=['DATA_ULTIMA_COMPRA', 'REPRESENTANTE'], 
        ascending=[False, True], 
        inplace=True
    )

    # 7. Selecionar e Renomear colunas
    df_final_inativos = df_tabela_inativos[[
        'NOME', 
        'REPRESENTANTE', 
        'UF', # NOVO: Incluí a UF na tabela para facilitar a análise com o filtro
        'MÊS_ULTIMA_COMPRA'
    ]].rename(columns={
        'NOME': 'Nome do Cliente',
        'REPRESENTANTE': 'Representante',
        'UF': 'UF',
        'MÊS_ULTIMA_COMPRA': 'Mês da Última Compra'
    })

    # 8. Exibir a Tabela
    st.dataframe(
        df_final_inativos,
        width='stretch',
        hide_index=True 
    )

else:
    # Mostra a mensagem de sucesso se não houver inativos dentro do conjunto filtrado
    st.success(f"🎉 Não há clientes inativos no conjunto de dados filtrado para o mês de {mes_referencia}!")




# --- Tabela 9: Análise de Queda (Período 1 vs. Período 2) ---
st.markdown("---")
st.subheader("9. Análise de Queda Comparativa (Período 1 vs. Período 2)")

# --- NOVO: Seletor de Métrica (R$ ou KG) ---
# Usamos colunas para posicionar o seletor acima da tabela, mas na mesma seção
col_info, col_seletor = st.columns([2, 1])

with col_seletor:
    metrica_selecionada = st.radio(
        "Métrica de Análise:",
        options=['Volume (KG)', 'Vendas (R$)'],
        index=0, # Inicia em KG por padrão
        key='tabela9_metrica'
    )

    

# Define a coluna de dados e o formato com base na seleção
if 'KG' in metrica_selecionada:
    COLUNA_DADOS = 'FATURA_KG'
    SUFIXO_COLUNA = '(KG)'
    FORMATO_NUMERICO = ',.2f'
    LABEL_METRICA = 'Volume'
else:
    COLUNA_DADOS = 'FATURA_RS'
    SUFIXO_COLUNA = '(R$)'
    FORMATO_NUMERICO = ',.2f' # Formato que será corrigido para BR no Pandas
    LABEL_METRICA = 'Venda'
    

# Leitura dos filtros de Mês e Ano
meses_filtrados = st.session_state.get('filter_MÊS', [])
anos_filtrados = st.session_state.get('filter_ANO', [])

# 1. Criar a lista completa de PERÍODOS (Mês/Ano)
periodos_completos = []
mes_map_ordem = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

for ano_sel in sorted(anos_filtrados):
    for mes_sel in sorted(meses_filtrados, key=lambda m: mes_map_ordem.get(m.lower().strip(), 0)):
        periodos_completos.append((ano_sel, mes_sel))


# 2. Verificar se o número de períodos é par
num_periodos = len(periodos_completos)
df_final = pd.DataFrame()

if not df_filtrado.empty and num_periodos > 0 and num_periodos % 2 == 0:
    
    meio = num_periodos // 2
    periodo_1_list = periodos_completos[:meio]
    periodo_2_list = periodos_completos[meio:]
    
    periodo_1_str = ", ".join([f"{m}/{a}" for a, m in periodo_1_list])
    periodo_2_str = ", ".join([f"{m}/{a}" for a, m in periodo_2_list])
    
    with col_info:
        st.markdown(f"""
        **Grupos de Comparação (dentro dos filtros aplicados):**
        * **Período 1:** {periodo_1_str}
        * **Período 2:** {periodo_2_str}
        """)
    
    # 3. BASE DE DADOS: Usamos o DF FILTRADO
    df_comparacao = df_filtrado.copy()

    df_comparacao['IS_P1'] = df_comparacao.apply(
        lambda row: (row['ANO'], row['MÊS']) in periodo_1_list, axis=1
    )
    df_comparacao['IS_P2'] = df_comparacao.apply(
        lambda row: (row['ANO'], row['MÊS']) in periodo_2_list, axis=1
    )

    # 5. Agrupar os valores por cliente e por período (usando a COLUNA_DADOS DINÂMICA)
    
    df_p1 = df_comparacao[df_comparacao['IS_P1']].groupby('NOME')[COLUNA_DADOS].sum().reset_index()
    df_p1.rename(columns={COLUNA_DADOS: 'P1_VALOR'}, inplace=True)
    
    df_p2 = df_comparacao[df_comparacao['IS_P2']].groupby('NOME')[COLUNA_DADOS].sum().reset_index()
    df_p2.rename(columns={COLUNA_DADOS: 'P2_VALOR'}, inplace=True)

    # 6. Merge dos Volumes e Cálculo da Queda/Crescimento
    df_resultado = pd.merge(df_p1, df_p2, on='NOME', how='outer').fillna(0)
    
    df_resultado['QUEDA_VALOR'] = df_resultado['P1_VALOR'] - df_resultado['P2_VALOR']

    # 7. Filtrar apenas as Quedas (QUEDA_VALOR > 0)
    df_queda = df_resultado[df_resultado['QUEDA_VALOR'] > 0].copy()

    if not df_queda.empty:
        
        # 8. Trazer a UF
        df_caracteristicas = df_filtrado[['NOME', 'UF']].drop_duplicates(subset=['NOME'])
        df_final = pd.merge(df_queda, df_caracteristicas, on='NOME', how='left')
        
        # 9. Ordenar pela maior queda
        df_final.sort_values(by='QUEDA_VALOR', ascending=False, inplace=True)
        
        # 10. Selecionar e Renomear Colunas
        df_final = df_final[[
            'NOME', 
            'UF', 
            'P1_VALOR', 
            'P2_VALOR', 
            'QUEDA_VALOR'
        ]].rename(columns={
            'NOME': 'Nome do Cliente',
            'UF': 'UF',
            'P1_VALOR': f'{LABEL_METRICA} (Período 1) {SUFIXO_COLUNA}',
            'P2_VALOR': f'{LABEL_METRICA} (Período 2) {SUFIXO_COLUNA}',
            'QUEDA_VALOR': f'Queda no {LABEL_METRICA} {SUFIXO_COLUNA}'
        })

        # --- Tabela 9: Análise de Queda Comparativa ---

# --- Tabela 9: Análise de Queda Comparativa (FINAL) ---

# 10.5. PREPARAÇÃO DOS DATAFRAMES
df_final_raw = df_final.copy() 

# df_display contém as colunas formatadas como strings para exibição
df_display = df_final.copy()
colunas_a_formatar = [col for col in df_display.columns if 'Período' in col or 'Queda' in col]

for col in colunas_a_formatar:
    df_display[col] = df_display[col].map(
        lambda x: f'{x:{FORMATO_NUMERICO}}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    )

# 11. INICIALIZAÇÃO DE OBSERVAÇÕES E ESTADO
observacoes = carregar_observacoes()
df_final_raw['idx_posicao'] = range(len(df_final_raw)) # Índice de posição
df_display['idx_posicao'] = range(len(df_display)) # Índice de posição

if 'cliente_aberto' not in st.session_state:
    st.session_state['cliente_aberto'] = None

# --- DEFINIÇÃO DO LAYOUT ---
#st.subheader("9. Análise de Queda Comparativa (Período 1 vs. Período 2)")

# Larguras das colunas: [Botão, Ícone, Cliente, UF, Período 1, Período 2, Queda]
colunas_widths = [0.4, 0.4, 3, 1, 1.5, 1.5, 1.5] 
colunas_nomes = ['Abrir', 'Obs', 'Cliente', 'UF', 'Período 1 (R$)', 'Período 2 (R$)', 'Queda (R$)']

# 1. EXIBIR CABEÇALHO (FIXO)
cols_header = st.columns(colunas_widths)
for col_name, col_obj in zip(colunas_nomes, cols_header):
    # Usamos st.markdown para reduzir o espaçamento
    col_obj.markdown(f"**{col_name}**")
#st.markdown("---") 

# --- INÍCIO DO CONTAINER COM BARRA DE ROLAGEM (ALTURA FIXA) ---
with st.container(height=400, border=True): 
    
    # 2. Renderização Linha por Linha
    for index, row in df_final_raw.iterrows():
        
        cliente = row['Nome do Cliente']
        obs_icon = '📝' if cliente in observacoes else ''
        
        # Cria as colunas para a linha de dados
        cols = st.columns(colunas_widths)
        
        # Coluna 1: O PEQUENO BOTÃO
        with cols[0]:
            # Usamos o emoji no botão e key única
            if st.button("✏️", key=f"btn_open_{index}"):
                st.session_state['cliente_aberto'] = cliente
                st.rerun()

        # Obter a linha formatada para exibição (usamos o índice de posição)
        display_row = df_display.iloc[row['idx_posicao']]
        
        # Colunas 2 a 7: Dados
        cols[1].markdown(obs_icon)
        cols[2].markdown(cliente)
        cols[3].markdown(row['UF'])
        cols[4].markdown(display_row.get(f'{LABEL_METRICA} (Período 1) {SUFIXO_COLUNA}', 'N/D'))
        cols[5].markdown(display_row.get(f'{LABEL_METRICA} (Período 2) {SUFIXO_COLUNA}', 'N/D'))
        cols[6].markdown(display_row.get(f'Queda no {LABEL_METRICA} {SUFIXO_COLUNA}', 'N/D'))

# --- FIM DO CONTAINER ---

# --- 3. LÓGICA DE EDIÇÃO (FORA DO CONTAINER) ---
# O Textarea aparecerá logo abaixo da tabela.

cliente_aberto = st.session_state.get('cliente_aberto')

if cliente_aberto:
    
    st.markdown("---")
    st.subheader(f"✏️ Observação para: **{cliente_aberto}**")

    obs_existente = observacoes.get(cliente_aberto, "")

    # Textarea para observação
    nova_observacao = st.text_area(
        "Insira sua observação aqui:", 
        value=obs_existente, 
        height=150,
        key=f"obs_text_area_{cliente_aberto}"
    )

    col_salvar, col_cancelar, col_fechar = st.columns([1, 1, 4])

    with col_salvar:
        if st.button("💾 Salvar", key="btn_save_final", type="primary"):
            if nova_observacao.strip():
                observacoes[cliente_aberto] = nova_observacao.strip()
            elif cliente_aberto in observacoes:
                del observacoes[cliente_aberto]
                
            salvar_observacoes(observacoes)
            st.session_state['cliente_aberto'] = None # Fecha a área
            st.toast("Observação salva! Recarregando...", icon='📝')
            st.rerun() 

    with col_cancelar:
        if st.button("❌ Cancelar", key="btn_cancel_final"):
            st.info("Edição cancelada.")
            st.session_state['cliente_aberto'] = None # Fecha a área
            st.rerun()

    with col_fechar:
        if st.button("Fechar Área", key="btn_close_final"):
            st.session_state['cliente_aberto'] = None # Fecha a área
            st.rerun() 
            
# 4. Lógica da Mensagem Final
elif df_final.empty:
    st.success(f"Nenhum cliente no conjunto filtrado teve queda no {LABEL_METRICA}...")

else:
    # Aviso de número ímpar ou sem dados
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    elif num_periodos % 2 != 0:
        st.warning("Selecione um número **PAR** de meses/anos para que a comparação entre Períodos 1 e 2 possa ser feita.")
    else:
        st.warning("Por favor, selecione meses e anos nos filtros laterais para iniciar a análise comparativa.")
    st.info(f"Períodos detectados: {num_periodos}")
    excel_data = to_excel(df_final_raw)
    
    st.download_button(
        label="Exportar para Excel 📊",
        data=excel_data,
        file_name='Analise_Queda_Clientes.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        type="primary"
    )

# Opcional: Mostrar os dados filtrados em uma tabela
if st.checkbox("Mostrar dados filtrados (Tabela)"):

    st.dataframe(df_filtrado)   



