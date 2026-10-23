import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Analisador de Linhagens e Idades", layout="wide")

st.title("🧬 Analisador Estatístico de Linhagens e Bioterio")
st.write("Faça o upload do seu arquivo, selecione as colunas correspondentes e aplique os filtros desejados.")

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
        st.sidebar.info("Selecione quais colunas da sua planilha correspondem a cada dado:")
        
        # Encontra índices padrão para ajudar o usuário se possível
        def encontrar_padrao(termo, lista):
            for i, col in enumerate(lista):
                if termo in str(col).lower():
                    return i
            return 0

        # Cria os seletores manuais baseados nas colunas REAIS da planilha
        idx_idade = encontrar_padrao("idade", colunas_originais)
        idx_linha = encontrar_padrao("linhagem", colunas_originais)
        idx_sexo = encontrar_padrao("sexo", colunas_originais)
        idx_desc = encontrar_padrao("descarte", colunas_originais)
        
        c_idade = st.sidebar.selectbox("Coluna de IDADE:", colunas_originais, index=idx_idade)
        c_linha = st.sidebar.selectbox("Coluna de LINHAGEM:", colunas_originais, index=idx_linha)
        c_sexo = st.sidebar.selectbox("Coluna de SEXO:", colunas_originais, index=idx_sexo)
        
        # Coluna opcional de descarte
        adicionar_descarte = st.sidebar.checkbox("Minha planilha tem coluna de Descarte", value=True)
        c_desc = None
        if adicionar_descarte:
            c_desc = st.sidebar.selectbox("Coluna de DESCARTE:", colunas_originais, index=idx_desc)

        # --- LIMPEZA PROFUNDA DOS DADOS SELECIONADOS ---
        # Criamos um dataframe limpo apenas com o que importa
        df_clean = df.copy()
        
        # Remove espaços extras dos nomes de texto e converte para maiúsculo
        df_clean['linhagem_clean'] = df_clean[c_linha].astype(str).str.strip().str.upper()
        df_clean['sexo_clean'] = df_clean[c_sexo].astype(str).str.strip().str.upper()
        
        # Trata idades convertendo o que for texto/inválido para número (NaN) e dropando
        df_clean[c_idade] = pd.to_numeric(df_clean[c_idade], errors='coerce')
        df_clean = df_clean.dropna(subset=[c_idade])
        
        # Filtra textos vazios ou nulos que viraram strings como "NAN" ou "NONE"
        df_clean = df_clean[~df_clean['linhagem_clean'].isin(['NAN', 'NONE', '', 'NAT'])]
        df_clean = df_clean[~df_clean['sexo_clean'].isin(['NAN', 'NONE', '', 'NAT'])]
        
        if c_desc:
            df_clean['descarte_clean'] = df_clean[c_desc].astype(str).str.strip().str.upper()
            df_clean = df_clean[~df_clean['descarte_clean'].isin(['NAN', 'NONE', '', 'NAT'])]

        # Criando a string combinada padrão solicitada: ex: BALB(M)
        df_clean['linhagem_sexo'] = df_clean['linhagem_clean'] + "(" + df_clean['sexo_clean'] + ")"

        # --- PAINEL DE FILTROS NA SIDEBAR ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("3. Filtros Ativos")
        
        # Filtro de Linhagens (Vem com todas selecionadas)
        todas_linhagens = sorted(df_clean['linhagem_clean'].unique())
        sub_linhagens = st.sidebar.multiselect("Filtrar Linhagens:", todas_linhagens, default=todas_linhagens)
        
        # Filtro de Tipo de Descarte
        sub_descartes = []
        if c_desc:
            todos_descartes = sorted(df_clean['descarte_clean'].unique())
            sub_descartes = st.sidebar.multiselect("Filtrar Tipo de Descarte (Vazio = Todos):", todos_descartes, default=[])
            
        # Aplicação cirúrgica dos filtros
        df_filtered = df_clean[df_clean['linhagem_clean'].isin(sub_linhagens)]
        if c_desc and len(sub_descartes) > 0:
            df_filtered = df_filtered[df_filtered['descarte_clean'].isin(sub_descartes)]
            
        # Validação final anti-quebra
        if df_filtered.empty:
            st.error("⚠️ Nenhum dado sobrou. Verifique se as 3 colunas selecionadas no passo 2 possuem dados numéricos válidos e preenchidos.")
            st.write("Amostra crua dos dados originais enviados:")
            st.dataframe(df.head(5))
            st.stop()

        # --- VISUALIZAÇÃO PADRÃO ---
        st.subheader("📊 Gráficos de Distribuição por Linhagem e Sexo")
        tab1, tab2 = st.tabs(["Histograma Comparativo", "Boxplot de Outliers"])
        
        with tab1:
            fig_hist = px.histogram(
                df_filtered, 
                x=c_idade, 
                color='linhagem_sexo', 
                barmode='overlay', 
                marginal='rug',
                title="Distribuição das Faixas de Idade por Linhagem (Sexo)",
                labels={c_idade: f"Idade ({c_idade})", 'linhagem_sexo': "Linhagem (Sexo)"},
                opacity=0.65,
                nbins=30
            )
            fig_hist.update_layout(height=550, hovermode="x unified")
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with tab2:
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
        
        linhagens_unicas = df_filtered['linhagem_clean'].unique()
        grupos_linhagem = [df_filtered[df_filtered['linhagem_clean'] == lin][c_idade].values for lin in linhagens_unicas]
        
        if len(grupos_linhagem) > 1 and all(len(g) > 2 for g in grupos_linhagem):
            st.markdown("**Comparação de Idade entre Linhagens Diferentes:**")
            tamanho_amostra = min(len(df_filtered), 500)
            stat_sh, p_sh = stats.shapiro(df_filtered[c_idade].sample(tamanho_amostra, random_state=42))
            
            if p_sh > 0.05:
                f_stat, p_val = stats.f_oneway(*grupos_linhagem)
                teste_nome = "ANOVA (Paramétrico)"
            else:
                f_stat, p_val = stats.kruskal(*grupos_linhagem)
                teste_nome = "Kruskal-Wallis (Não-Paramétrico)"
                
            if p_val < 0.05:
                st.error(f"🔴 **Diferença Significativa Encontrada!** ({teste_nome}: p-valor = {p_val:.5f}). As idades variam de forma relevante entre as linhagens.")
            else:
                st.info(f"🟢 **Sem Diferença Significativa.** ({teste_nome}: p-valor = {p_val:.5f}). As idades médias das linhagens são estatisticamente similares.")
        
        machos = df_filtered[df_filtered['sexo_clean'].isin(['M', 'MACHO', 'MALE'])][c_idade].values
        femeas = df_filtered[df_filtered['sexo_clean'].isin(['F', 'FEMEA', 'FEMALE', 'FE'])][c_idade].values
        
        if len(machos) > 2 and len(femeas) > 2:
            st.markdown("**Comparação de Idade entre Machos vs Fêmeas (Geral):**")
            t_stat, p_val_sex = stats.mannwhitneyu(machos, femeas, alternative='two-sided')
            
            if p_val_sex < 0.05:
                st.error(f"🔴 **Diferença Significativa entre Sexos!** (Mann-Whitney U: p-valor = {p_val_sex:.5f}). Machos e fêmeas possuem idades de descarte/análise significativamente diferentes.")
            else:
                st.info(f"🟢 **Sem Diferença Significativa entre Sexos.** (Mann-Whitney U: p-valor = {p_val_sex:.5f}). Não há disparidade estatística nas idades de machos e fêmeas.")

    except Exception as e:
        st.error(f"Erro crítico ao processar o arquivo: {e}")
else:
    st.info("📊 Aguardando o envio do arquivo na barra lateral para renderizar o histograma e filtros padrão.")
