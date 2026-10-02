import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="Análise Biotério - Linhagens", layout="wide", page_icon="🧬")

st.title("🧬 Painel Estatístico de Descarte e Eutanásia")
st.markdown("Faça o upload da sua planilha para analisar os dados de forma segmentada e precisa.")

# Upload de arquivos (Aceita Excel ou CSV)
uploaded_file = st.file_uploader("Suba sua planilha Excel (.xlsx) ou CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    df = None
    
    # --- LEITURA BLINDADA ---
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin1')
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
        else:
            df = pd.read_excel(uploaded_file)
            
    except Exception as e:
        st.error(f"❌ Erro crítico ao ler o arquivo: {e}")
        st.stop()

    if df is not None and not df.empty:
        # --- TRATAMENTO AUTOMÁTICO DE DADOS ---
        df.columns = df.columns.str.strip()

        # Verificar colunas obrigatórias
        colunas_obrigatorias = ['Linhagem', 'Quantidade', 'Idade', 'Sexo']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltantes:
            st.error(f"❌ Erro na estrutura! A planilha precisa conter as colunas: {', '.join(colunas_faltantes)}")
            st.stop()

        # Padronização de textos
        df['Linhagem'] = df['Linhagem'].astype(str).str.strip().str.upper()
        df['Sexo'] = df['Sexo'].astype(str).str.strip().str.upper()

        # Correção estrita de decimais da Idade
        if df['Idade'].dtype == 'object':
            df['Idade'] = df['Idade'].astype(str).str.replace(',', '.').str.strip()
        df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce').fillna(0)

        # Quantidade como número inteiro
        df['Quantidade'] = pd.to_numeric(df['Quantidade'], errors='coerce').fillna(0).astype(int)

        # Renomeação da 5ª coluna (Destino: E/Z)
        if len(df.columns) >= 5:
            df = df.rename(columns={df.columns[4]: 'Destino'})
            df['Destino'] = df['Destino'].astype(str).str.strip().str.upper()
        else:
            df['Destino'] = 'N/A'

        # ----------------------------------------------------
        # PAINEL DE MULTI-FILTROS NA BARRA LATERAL (ESQUERDA)
        # ----------------------------------------------------
        st.sidebar.header("🔍 Painel de Filtros Avançados")
        st.sidebar.markdown("Combine as opções abaixo para isolar as subpopulações do biotério:")

        # 1. Filtro de Linhagem
        lista_linhagens = ["Todas"] + sorted(df['Linhagem'].dropna().unique().tolist())
        linhagem_sel = st.sidebar.selectbox("1. Filtrar por Linhagem:", lista_linhagens)

        # 2. Filtro de Sexo
        lista_sexos = ["Todos"] + sorted(df['Sexo'].dropna().unique().tolist())
        sexo_sel = st.sidebar.selectbox("2. Filtrar por Sexo:", lista_sexos)

        # 3. Filtro de Destino (Eutanásia/Zoológico)
        lista_destinos = ["Todos"] + sorted(df['Destino'].dropna().unique().tolist())
        destino_sel = st.sidebar.selectbox("3. Filtrar por Destino (E/Z):", lista_destinos)

        # --- APLICAÇÃO DOS FILTROS SEQUENCIAIS ---
        df_filtrado = df.copy()
        
        if linhagem_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado['Linhagem'] == linhagem_sel]
            
        if sexo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Sexo'] == sexo_sel]
            
        if destino_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Destino'] == destino_sel]

        # --- VISUALIZAÇÃO DA TABELA FILTRADA ---
        st.subheader(f"📋 Dados em Análise (Exibindo {len(df_filtrado)} de {len(df)} linhas totais)")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- SEÇÃO DE ANÁLISES ---
        st.header("📊 Relatórios e Estatísticas Combinadas")
        tab1, tab2, tab3 = st.tabs(["📉 Métricas por Idade Exata", "📈 Análise Visual Separada", "💾 Exportação"])

        with tab1:
            st.subheader("Contagem Estrita do Grupo Filtrado")
            df_grupos = df_filtrado.groupby(['Linhagem', 'Idade', 'Sexo', 'Destino']).agg(
                Total_Animais_Descartados=('Quantidade', 'sum'),
                Lotes_Registrados=('Quantidade', 'count')
            ).reset_index()
            st.dataframe(df_grupos, use_container_width=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Proporção de Destino Atual")
                df_dest = df_filtrado.groupby('Destino').agg(Total=('Quantidade','sum')).reset_index()
                st.dataframe(df_dest, use_container_width=True)
            with col_b:
                st.subheader("Resumo Fisiológico das Idades")
                resumo_idade_real = df_filtrado.groupby('Linhagem')['Idade'].describe()[['min', '50%', 'max', 'count']]
                st.dataframe(resumo_idade_real, use_container_width=True)

        with tab2:
            st.subheader("Gráficos de Distribuição Estrita")
            
            fig_scatter = px.scatter(
                df_filtrado, x='Idade', y='Quantidade', color='Linhagem', symbol='Sexo', size='Quantidade',
                title="Dispersão: Distribuição Fisiológica do Grupo Filtrado",
                labels={'Idade': 'Idade Fisiológica'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_bar_idade = px.bar(
                    df_grupos, x='Idade', y='Total_Animais_Descartados', color='Sexo', barmode='group',
                    title="Volume Total por Idade e Sexo", text_auto=True
                )
                st.plotly_chart(fig_bar_idade, use_container_width=True)
            with col_g2:
                fig_box_real = px.box(
                    df_filtrado, x='Linhagem', y='Idade', color='Sexo', points="all",
                    title="Janela Biológica de Idades Atendidas"
                )
                st.plotly_chart(fig_box_real, use_container_width=True)

        with tab3:
            st.subheader("Baixar Planilha de Análise Gerada")
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df_grupos.to_excel(writer, sheet_name='Segmentacao Estrita', index=False)
                df_filtrado.to_excel(writer, sheet_name='Dados Filtrados', index=False)
                    
            st.download_button(
                label="📥 Baixar Dados Segregados por Filtro Atual (Excel)",
                data=output_excel.getvalue(),
                file_name="relatorio_customizado_bioterio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.warning("⚠️ Aguardando o upload do arquivo Excel ou CSV para iniciar as análises estatísticas.")
