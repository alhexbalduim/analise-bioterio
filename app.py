import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Analisador de Linhagens e Idades", layout="wide")

st.title("🧬 Analisador Estatístico de Linhagens e Bioterio")
st.write("Analise faixas de idade calculadas estatisticamente por grupos combinados de Linhagem(Sexo), aplique filtros customizados e visualize a contagem de descartes.")

# Sidebar para Upload
uploaded_file = st.sidebar.file_uploader("1. Envie seu arquivo (XLSX, XLS ou CSV)", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        # Leitura do arquivo
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success("Arquivo carregado com sucesso!")
        
        # Lista real de colunas encontradas na planilha do usuário
        colunas_originais = list(df.columns)
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("2. Mapeamento de Colunas")
        
        def encontrar_padrao(termo, lista):
            for i, col in enumerate(lista):
                if termo in str(col).lower():
                    return i
            return 0

        c_idade = st.sidebar.selectbox("Coluna de IDADE:", colunas_originais, index=encontrar_padrao("idade", colunas_originais))
        c_linha = st.sidebar.selectbox("Coluna de LINHAGEM:", colunas_originais, index=encontrar_padrao("linhagem", colunas_originais))
        c_sexo = st.sidebar.selectbox("Coluna de SEXO:", colunas_originais, index=encontrar_padrao("sexo", colunas_originais))
        
        adicionar_descarte = st.sidebar.checkbox("Minha planilha tem coluna de Descarte", value=True)
        c_desc = None
        if adicionar_descarte:
            c_desc = st.sidebar.selectbox("Coluna de DESCARTE:", colunas_originais, index=encontrar_padrao("descarte", colunas_originais))

        # --- LIMPEZA PROFUNDA E CONSTRUÇÃO DOS GRUPOS ---
        df_clean = df.copy()
        df_clean['linhagem_clean'] = df_clean[c_linha].astype(str).str.strip().str.upper()
        df_clean['sexo_clean'] = df_clean[c_sexo].astype(str).str.strip().str.upper()
        
        df_clean[c_idade] = pd.to_numeric(df_clean[c_idade], errors='coerce')
        df_clean = df_clean.dropna(subset=[c_idade])
        
        df_clean = df_clean[~df_clean['linhagem_clean'].isin(['NAN', 'NONE', '', 'NAT'])]
        df_clean = df_clean[~df_clean['sexo_clean'].isin(['NAN', 'NONE', '', 'NAT'])]
        
        if c_desc:
            df_clean['descarte_clean'] = df_clean[c_desc].astype(str).str.strip().str.upper()
            df_clean = df_clean[~df_clean['descarte_clean'].isin(['NAN', 'NONE', '', 'NAT'])]

        df_clean['linhagem_sexo'] = df_clean['linhagem_clean'] + "(" + df_clean['sexo_clean'] + ")"

        # --- CÁLCULO ESTATÍSTICO DO TAMANHO DO INTERVALO (BIN WIDTH) ---
        idades_reais = df_clean[c_idade].values
        n_amostra = len(idades_reais)
        
        if n_amostra > 1:
            # Regra de Freedman-Diaconis: Baseada na Amplitude Interquartil (IQR), ótima para dados reais com outliers
            q75, q25 = np.percentile(idades_reais, [75 ,25])
            iqr = q75 - q25
            
            if iqr > 0:
                tamanho_intervalo = 2 * iqr / (n_amostra ** (1/3))
            else:
                # Fallback para Regra de Sturges se o IQR for zero (todos os animais com idades muito parecidas)
                tamanho_intervalo = (idades_reais.max() - idades_reais.min()) / (np.log2(n_amostra) + 1)
            
            # Arredonda o tamanho do intervalo para um número inteiro amigável (mínimo de 1)
            tamanho_intervalo = max(1, int(np.round(tamanho_intervalo)))
        else:
            tamanho_intervalo = 5

        min_idade = int(np.floor(idades_reais.min()))
        max_idade = int(np.ceil(idades_reais.max()))
        
        # Cria as quebras (bins) baseadas no tamanho do intervalo calculado estatisticamente
        bins = list(range(min_idade, max_idade + tamanho_intervalo + 1, tamanho_intervalo))
        labels = [f"{bins[i]} a {bins[i+1]-1}" for i in range(len(bins)-1)]
        
        df_clean['faixa_idade'] = pd.cut(df_clean[c_idade], bins=bins, labels=labels, right=False)

        # --- PAINEL DE FILTROS NA SIDEBAR ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("3. Filtros Ativos")
        
        todos_grupos_combinados = sorted(df_clean['linhagem_sexo'].unique())
        sub_grupos = st.sidebar.multiselect(
            "Filtrar por Linhagem(Sexo):", 
            todos_grupos_combinados, 
            default=todos_grupos_combinados
        )
        
        sub_descartes = []
        if c_desc:
            todos_descartes = sorted(df_clean['descarte_clean'].unique())
            sub_descartes = st.sidebar.multiselect("Filtrar Tipo de Descarte (Vazio = Todos):", todos_descartes, default=[])
            
        df_filtered = df_clean[df_clean['linhagem_sexo'].isin(sub_grupos)]
        if c_desc and len(sub_descartes) > 0:
            df_filtered = df_filtered[df_filtered['descarte_clean'].isin(sub_descartes)]
            
        if df_filtered.empty:
            st.error("⚠️ Nenhum dado sobrou para a combinação de filtros selecionada.")
            st.stop()

        # --- VISUALIZAÇÃO GRÁFICA ---
        st.subheader("📊 Análise Visual de Distribuição e Descarte")
        
        # Informa ao usuário qual foi o intervalo calculado pelo algoritmo
        st.info(f"💡 **Cálculo de Distribuição Automático:** Com base na variabilidade dos dados entregues, o tamanho ideal calculado para cada intervalo de idade foi de **{tamanho_intervalo} dias/unidades**.")
        
        tab1, tab2, tab3 = st.tabs(["Contagem por Faixa de Idade (Estatístico)", "Histograma Contínuo", "Boxplot de Outliers"])
        
        with tab1:
            # Agrupa e conta usando as faixas calculadas estatisticamente
            df_counts = df_filtered.groupby(['faixa_idade', 'linhagem_sexo'], observed=False).size().reset_index(name='Quantidade de Descartes')
            
            fig_bar = px.bar(
                df_counts,
                x='faixa_idade',
                y='Quantidade de Descartes',
                color='linhagem_sexo',
                barmode='group',
                title=f"Quantidade de Descartes por Faixas Reais Calculadas (Intervalos de {tamanho_intervalo} em {tamanho_intervalo})",
                labels={'faixa_idade': 'Intervalos de Idade Calculados', 'linhagem_sexo': 'Linhagem (Sexo)'},
                text_auto=True
            )
            fig_bar.update_layout(height=550)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with tab2:
            fig_hist = px.histogram(
                df_filtered, 
                x=c_idade, 
                color='linhagem_sexo', 
                barmode='overlay', 
                marginal='rug',
                title="Distribuição de Frequência Contínua da Idade",
                labels={c_idade: f"Idade ({c_idade})", 'linhagem_sexo': "Linhagem (Sexo)"},
                opacity=0.65,
                nbins=len(bins) # Alinha o número de colunas com as quebras calculadas
            )
            fig_hist.update_layout(height=550, hovermode="x unified")
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with tab3:
            fig_box = px.box(
                df_filtered, 
                x='linhagem_sexo', 
                y=c_idade, 
                color='sexo_clean',
                points="all",
                title="Boxplot de Idades com Detecção de Outliers e Quartis",
                labels={c_idade: c_idade, 'linhagem_sexo': "Linhagem (Sexo)", 'sexo_clean': "Sexo"}
            )
            fig_box.update_layout(height=550)
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown("---")

        # --- EXTRAÇÃO ESTATÍSTICA MÁXIMA ---
        st.subheader("📈 Relatório Estatístico Agrupado")
        
        resumo_estatistico = df_filtered.groupby('linhagem_sexo')[c_idade].agg(
            Total_N='count',
            Média='mean',
            Mediana='median',
            Desvio_Padrão=lambda x: np.std(x, ddof=1) if len(x) > 1 else 0,
            Erro_Padrão=lambda x: stats.sem(x) if len(x) > 1 else 0,
            Mínimo='min',
            Máximo='max'
        ).reset_index()
        
        for col in ['Média', 'Mediana', 'Desvio_Padrão', 'Erro_Padrão']:
            resumo_estatistico[col] = resumo_estatistico[col].round(3)
            
        st.dataframe(resumo_estatistico, use_container_width=True, hide_index=True)

        # --- TESTES DE HIPÓTESES AUTOMÁTICOS ---
        st.markdown("---")
        st.subheader("🔬 Inferência Estatística Avançada")
        
        grupos_teste = [df_filtered[df_filtered['linhagem_sexo'] == g][c_idade].values for g in df_filtered['linhagem_sexo'].unique()]
        
        if len(grupos_teste) > 1 and all(len(g) > 2 for g in grupos_teste):
            st.markdown("**Comparação estatística entre os grupos selecionados na barra lateral:**")
            tamanho_amostra = min(len(df_filtered), 500)
            stat_sh, p_sh = stats.shapiro(df_filtered[c_idade].sample(tamanho_amostra, random_state=42))
            
            if p_sh > 0.05:
                f_stat, p_val = stats.f_oneway(*grupos_teste)
                teste_nome = "ANOVA (Paramétrico)"
            else:
                f_stat, p_val = stats.kruskal(*grupos_teste)
                teste_nome = "Kruskal-Wallis (Não-Paramétrico)"
                
            if p_val < 0.05:
                st.error(f"🔴 **Diferença Significativa Encontrada!** ({teste_nome}: p-valor = {p_val:.5f}). As idades variam de forma relevante entre os grupos filtrados.")
            else:
