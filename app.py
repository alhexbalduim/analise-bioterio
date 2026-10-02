import streamlit as st
import pandas as pd
import plotly.express as px
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="Análise Biotério - Linhagens", layout="wide", page_icon="🧬")

st.title("🧬 Painel Estatístico de Descarte e Eutanásia")
st.markdown("Faça o upload da sua planilha para analisar os dados sem misturar Linhagens, Idades ou Sexo.")

# Upload de arquivos (Aceita Excel ou CSV)
uploaded_file = st.file_uploader("Suba sua planilha Excel (.xlsx) ou CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    df = None
    
    # --- LEITURA BLINDADA CONTRA ERROS DE UNICODE E SEPARADOR ---
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                # Tenta ler no padrão Excel/BR (codificação latina e detectando o separador)
                df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin1')
            except Exception:
                # Segunda alternativa: tenta codificação universal UTF-8 se a anterior falhar
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
        else:
            # Leitura nativa para arquivos Excel (.xlsx)
            df = pd.read_excel(uploaded_file)
            
    except Exception as e:
        st.error(f"❌ Erro crítico ao ler o arquivo: {e}")
        st.stop()

    if df is not None and not df.empty:
        # --- TRATAMENTO AUTOMÁTICO DE DADOS ---
        
        # Remover espaços em branco nos nomes das colunas
        df.columns = df.columns.str.strip()

        # Verificar se as colunas essenciais existem na planilha para evitar KeyError
        colunas_obrigatorias = ['Linhagem', 'Quantidade', 'Idade', 'Sexo']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltantes:
            st.error(f"❌ Erro na estrutura do arquivo! A planilha precisa conter as colunas: {', '.join(colunas_faltantes)}")
            st.info("Verifique se os nomes das colunas na sua planilha estão exatamente iguais ao exemplo original.")
            st.stop()

        # 1. Unifica caixa alta/baixa (ex: Balb e BALB viram BALB) e limpa espaços
        df['Linhagem'] = df['Linhagem'].astype(str).str.strip().str.upper()
        df['Sexo'] = df['Sexo'].astype(str).str.strip().str.upper()

        # 2. Corrige formatação de decimais da Idade e blinda contra textos/vazios inválidos
        if df['Idade'].dtype == 'object':
            df['Idade'] = df['Idade'].astype(str).str.replace(',', '.').str.strip()
        
        # Converte para número e transforma qualquer texto inválido ou vazio em nulo (NaN) sem travar
        df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
        
        # Remove linhas onde a idade ou linhagem ficaram completamente inválidas ou vazias
        df = df.dropna(subset=['Idade', 'Linhagem'])

        # 3. Garante que a quantidade seja numérica inteira
        df['Quantidade'] = pd.to_numeric(df['Quantidade'], errors='coerce').fillna(0).astype(int)

        # 4. Renomeia dinamicamente a 5ª coluna para "Destino" (onde fica E/Z), independente do tamanho do cabeçalho
        if df.shape[1] >= 5:
            df = df.rename(columns={df.columns[4]: 'Destino'})
            df['Destino'] = df['Destino'].astype(str).str.strip().str.upper()
        else:
            df['Destino'] = 'N/A'

        # --- VISUALIZAÇÃO PRINCIPAL ---
        st.subheader("📋 Dados Carregados com Sucesso")
        st.dataframe(df, use_container_width=True)

        # --- FILTROS DE ISOLAMENTO NA BARRA LATERAL ---
        st.sidebar.header("🔍 Filtros de Isolamento")
        todas_linhagens = ["Todas"] + sorted(df['Linhagem'].dropna().unique().tolist())
        linhagem_sel = st.sidebar.selectbox("Escolha a Linhagem para Isolar:", todas_linhagens)

        # Aplica o filtro selecionado pelo usuário
        df_filtrado = df if linhagem_sel == "Todas" else df[df['Linhagem'] == linhagem_sel]

        # --- SEÇÃO DE ANÁLISES ---
        st.header(f"📊 Estatísticas Detalhadas - Grupo: {linhagem_sel}")
        tab1, tab2, tab3 = st.tabs(["📉 Métricas por Idade Exata", "📈 Análise Visual Separada", "💾 Exportação"])

        with tab1:
            st.subheader("Contagem Estrita por Linhagem, Idade e Sexo")
            st.markdown("Esta tabela detalha os totais exatos sem misturar animais novos com animais velhos:")
            
            # Agrupamento refinado por subgrupos biológicos reais
            df_grupos = df_filtrado.groupby(['Linhagem', 'Idade', 'Sexo', 'Destino']).agg(
                Total_Animais_Descartados=('Quantidade', 'sum'),
                Lotes_Registrados=('Quantidade', 'count')
            ).reset_index()
            
            st.dataframe(df_grupos, use_container_width=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Proporção de Destino (Eutanásia vs Zoológico)")
                df_dest = df_filtrado.groupby('Destino').agg(Total=('Quantidade','sum')).reset_index()
                st.dataframe(df_dest, use_container_width=True)
            with col_b:
                st.subheader("Faixas de Idade Atendidas (Resumo)")
                resumo_idade_real = df_filtrado.groupby('Linhagem')['Idade'].describe()[['min', '50%', 'max', 'count']]
                st.dataframe(resumo_idade_real, use_container_width=True)

        with tab2:
            st.subheader("Gráficos de Distribuição Estrita")
            st.markdown("*Dica: Use a câmera fotográfica no canto superior direito de cada gráfico para baixá-los como imagem.*")
            
            # Gráfico de dispersão inteligente: evita o efeito de caixa única
            fig_scatter = px.scatter(
                df_filtrado, x='Idade', y='Quantidade', color='Linhagem', symbol='Sexo', size='Quantidade',
                title="Dispersão: Cada ponto é um registro real no tempo",
                labels={'Idade': 'Idade Fisiológica'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_bar_idade = px.bar(
                    df_grupos, x='Idade', y='Total_Animais_Descartados', color='Sexo', barmode='group',
                    facet_row='Destino', title="Total de Animais por Idades Fisiológicas e Destino", text_auto=True
                )
                st.plotly_chart(fig_bar_idade, use_container_width=True)
            with col_g2:
                fig_box_real = px.box(
                    df_filtrado, x='Linhagem', y='Idade', color='Sexo', points="all",
                    title="Janela Biológica de Idades por Linhagem"
                )
                st.plotly_chart(fig_box_real, use_container_width=True)

        with tab3:
            st.subheader("Baixar Planilha de Análise Gerada")
            
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df_grupos.to_excel(writer, sheet_name='Segmentacao Estrita', index=False)
                if linhagem_sel == "Todas":
                    resumo_idade_real.to_excel(writer, sheet_name='Resumo Idades')
                    
            st.download_button(
                label="📥 Baixar Dados Segregados por Linhagem/Idade (Excel)",
                data=output_excel.getvalue(),
                file_name=f"relatorio_bioterio_{linhagem_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("⚠️ O arquivo carregado está vazio.")
else:
    st.warning("⚠️ Aguardando o upload do arquivo Excel ou CSV para iniciar as análises estatísticas.")
