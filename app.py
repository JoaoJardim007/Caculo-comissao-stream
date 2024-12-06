# Importação de Bibliotecas
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings
warnings.filterwarnings('ignore')

# Configuração da Página
st.set_page_config(page_title="Dashboard de Vendas e Comissões", layout="wide", page_icon="💹")

# Estilos Personalizados
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        background-color: #005e4d;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho com Logo
logo_url = "https://pages.greatpages.com.br/lp.mundobiblico.com/1732818196/imagens/desktop/424273_1_17045703666599ae02ed082902047719.png"
st.sidebar.image(logo_url)  # Mantendo o tamanho original da imagem

# Função para leitura e limpeza de dados
def read_and_clean_data(uploaded_file):
    # Leitura do arquivo
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(uploaded_file)
    else:
        st.error('Tipo de arquivo não suportado.')
        return None

    # Limpeza e formatação dos dados
    df['Receita'] = df['Receita'].str.replace(r'R\$', '', regex=True).str.replace(r'\.', '', regex=True).str.replace(',', '.', regex=True).astype(float)
    df['Vendas'] = pd.to_numeric(df['Vendas'], errors='coerce').fillna(0).astype(int)
    df['Origem'] = df['Origem'].fillna('Desconhecido').str.strip()
    df['Mídia'] = df['Mídia'].fillna('Desconhecido').str.strip()
    df['Campanha'] = df['Campanha'].fillna('Desconhecido').str.strip()
    df['Conteúdo'] = df['Conteúdo'].fillna('Desconhecido').str.strip()
    df['Fonte'] = df['Fonte'].fillna('Desconhecido').str.strip()

    # Uniformização de nomes
    df['Origem'] = df['Origem'].replace({
        'joao-vendeu': 'João',
        'joao_vendeu?utm_source=João': 'João',
        'Auto': 'João',
        'Henrique': 'Henrique',
        'Claudia': 'Claudia',
        'Claudia-vendeu': 'Claudia',
        'Claudia-v': 'Claudia'
    })

    # Agrupar outros vendedores em "Outros"
    main_sellers = ['João', 'Claudia', 'Henrique']
    df['Origem'] = df['Origem'].apply(lambda x: x if x in main_sellers else 'Outros')

    return df

# Função para determinar a taxa de comissão
def get_commission_rate(vendedor, receita):
    if vendedor == 'João':
        if receita <= 15000:
            return 0.03
        elif receita <= 30000:
            return 0.04
        elif receita <= 60000:
            return 0.05
        elif receita <= 100000:
            return 0.06
        else:
            return 0.07
    elif vendedor in ['Claudia', 'Henrique']:
        if receita <= 10000:
            return 0.01
        elif receita <= 15000:
            return 0.02
        else:
            return 0.03
    else:
        return 0.00  # Outros não recebem comissão

# Função para calcular comissões
def calculate_commissions(df, api_cost):
    # Filtrar apenas os vendedores principais
    df_commission = df[df['Origem'].isin(['João', 'Claudia', 'Henrique'])].copy()

    # Subtrair o custo da API do WhatsApp da receita de João proporcionalmente
    joao_mask = df_commission['Origem'] == 'João'
    total_receita_joao = df_commission.loc[joao_mask, 'Receita'].sum()
    if total_receita_joao > 0:
        df_commission.loc[joao_mask, 'Proporcao'] = df_commission.loc[joao_mask, 'Receita'] / total_receita_joao
        df_commission.loc[joao_mask, 'Receita'] -= df_commission.loc[joao_mask, 'Proporcao'] * api_cost
    else:
        df_commission.loc[joao_mask, 'Proporcao'] = 0

    # Garantir que a receita não seja negativa
    df_commission['Receita'] = df_commission['Receita'].apply(lambda x: x if x > 0 else 0)

    # Calcular a receita total por vendedor (após dedução)
    receita_por_vendedor = df_commission.groupby('Origem')['Receita'].sum().reset_index()

    # Calcular a taxa de comissão para cada vendedor
    receita_por_vendedor['Taxa Comissão'] = receita_por_vendedor.apply(lambda row: get_commission_rate(row['Origem'], row['Receita']), axis=1)

    # Adicionar a taxa de comissão a cada venda
    df_commission = df_commission.merge(receita_por_vendedor[['Origem', 'Taxa Comissão']], on='Origem', how='left')

    # Calcular a comissão de cada venda
    df_commission['Comissão'] = df_commission['Receita'] * df_commission['Taxa Comissão']

    # Comissões totais por vendedor
    total_commission = df_commission.groupby('Origem')['Comissão'].sum().reset_index()

    return df_commission, total_commission

def main():
    st.title('💹 Dashboard de Vendas e Comissões')
    st.markdown("Bem-vindo(a) ao seu painel de controle! Aqui você pode analisar as vendas, comissões e desempenho das campanhas. Ajuste os filtros na barra lateral conforme necessário.")
    st.markdown("---")

    # Sidebar - Carregamento de Dados
    st.sidebar.header('Carregar Dados')
    uploaded_file = st.sidebar.file_uploader("Faça upload do arquivo (CSV, XLS, XLSX)", type=['csv', 'xls', 'xlsx'])

    if uploaded_file is not None:
        # Leitura e limpeza de dados
        df = read_and_clean_data(uploaded_file)

        # Entrada do Custo da API do WhatsApp
        st.sidebar.header('Custos Operacionais')
        api_cost = st.sidebar.number_input('Custo da API do WhatsApp (R$):', min_value=0.0, value=0.0, step=100.0)

        # Filtros Interativos
        st.sidebar.header('Filtros')
        vendedores = st.sidebar.multiselect('Selecione os Vendedores', options=df['Origem'].unique(), default=df['Origem'].unique())
        campanhas = st.sidebar.multiselect('Selecione as Campanhas', options=df['Campanha'].unique(), default=df['Campanha'].unique())
        midias = st.sidebar.multiselect('Selecione as Mídias', options=df['Mídia'].unique(), default=df['Mídia'].unique())

        # Aplicação dos filtros
        df_filtered = df[(df['Origem'].isin(vendedores)) & (df['Campanha'].isin(campanhas)) & (df['Mídia'].isin(midias))]

        # Cálculo das Comissões
        df_commission, total_commission = calculate_commissions(df_filtered, api_cost)

        # Métricas Gerais
        total_receita = df_filtered['Receita'].sum()
        total_vendas = df_filtered['Vendas'].sum()
        ticket_medio = total_receita / total_vendas if total_vendas else 0

        col_metrics = st.columns(4)
        col_metrics[0].metric("💰 Receita Total", f"R$ {total_receita:,.2f}")
        col_metrics[1].metric("🛒 Total de Vendas", f"{total_vendas}")
        col_metrics[2].metric("🎯 Ticket Médio", f"R$ {ticket_medio:,.2f}")
        col_metrics[3].metric("💵 Comissão Total", f"R$ {df_commission['Comissão'].sum():,.2f}")

        st.markdown("---")

        # Comissões por Vendedor
        st.subheader('Comissões por Vendedor')
        st.write("Abaixo, você pode ver a soma total de comissões geradas por cada vendedor após a dedução dos custos da API do WhatsApp.")
        st.dataframe(total_commission.style.format({'Comissão': 'R$ {:,.2f}'}))

        # Total de Vendas (Quantidade) por Vendedor
        vendas_por_vendedor = df_filtered.groupby('Origem')['Vendas'].sum().reset_index()

        # Gráficos lado a lado (Comissões e Vendas em Quantidade)
        col_graficos = st.columns(2)

        with col_graficos[0]:
            st.write("**Gráfico: Comissões por Vendedor**")
            fig_commission = px.bar(
                total_commission, 
                x='Origem', y='Comissão', 
                color='Origem', 
                text_auto=True, 
                title='Comissões por Vendedor',
                color_discrete_sequence=px.colors.qualitative.Dark2
            )
            fig_commission.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_commission, use_container_width=True)

        with col_graficos[1]:
            st.write("**Gráfico: Vendas (Quantidade) por Vendedor**")
            fig_vendas = px.bar(
                vendas_por_vendedor, 
                x='Origem', y='Vendas', 
                color='Origem', 
                text_auto=True,
                title='Vendas por Vendedor (Quantidade)',
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_vendas.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_vendas, use_container_width=True)

        # Nova Seção: Receita Total (R$) por Vendedor
        st.markdown("---")
        st.subheader('Receita Total por Vendedor (R$)')
        st.write("Aqui você pode visualizar o valor total em reais das vendas (Receita) de cada vendedor, após a aplicação dos filtros e dedução de custos da API para o João.")
        receita_vendedor = df_filtered.groupby('Origem')['Receita'].sum().reset_index().sort_values('Receita', ascending=False)
        st.dataframe(receita_vendedor.style.format({'Receita': 'R$ {:,.2f}'}))

        fig_receita_vendedor = px.bar(
            receita_vendedor,
            x='Origem',
            y='Receita',
            color='Origem',
            text='Receita',
            title='Receita por Vendedor (R$)',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_receita_vendedor.update_traces(textposition='inside', texttemplate='%{text:.2f}')
        fig_receita_vendedor.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_receita_vendedor, use_container_width=True)

        # Detalhes das Comissões
        with st.expander("Ver Detalhes das Comissões"):
            st.write("Aqui estão os detalhes de cada venda, já considerando a dedução do custo da API no caso do João.")
            st.dataframe(df_commission[['Origem', 'Receita', 'Taxa Comissão', 'Comissão']].style.format({
                'Receita': 'R$ {:,.2f}',
                'Comissão': 'R$ {:,.2f}',
                'Taxa Comissão': '{:.2%}'
            }))

        # Download do relatório de comissões
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv_commission = convert_df(df_commission)
        st.download_button(
            label="📥 Baixar Relatório de Comissões",
            data=csv_commission,
            file_name='comissoes.csv',
            mime='text/csv',
        )

        st.markdown("---")

        # Análise de Campanhas mais Eficientes
        st.subheader('Campanhas mais Eficientes')
        st.write("A tabela abaixo mostra quais campanhas geram mais receita e qual é o ticket médio por venda.")
        eficiencia_campanha = df_filtered.groupby('Campanha').agg({'Receita': 'sum', 'Vendas': 'sum'}).reset_index()
        eficiencia_campanha['Ticket Médio'] = eficiencia_campanha['Receita'] / eficiencia_campanha['Vendas']
        st.dataframe(eficiencia_campanha.sort_values('Receita', ascending=False).style.format({
            'Receita': 'R$ {:,.2f}',
            'Ticket Médio': 'R$ {:,.2f}'
        }))

        st.write("**Gráfico: Receita por Campanha**")
        fig_campanhas = px.bar(
            eficiencia_campanha, 
            x='Campanha', 
            y='Receita', 
            color='Campanha', 
            text='Receita', 
            title='Receita por Campanha',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_campanhas.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_campanhas, use_container_width=True)

    else:
        st.info('👈 Por favor, faça upload do arquivo de dados na barra lateral.')

if __name__ == '__main__':
    main()
