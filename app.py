import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Analisador de Linhagens e Idades", layout="wide")

st.title("🧬 Analisador Estatístico de Linhagens e Bioterio")
st.write("Faça o upload do seu arquivo para analisar as faixas de idade por linhagem/sexo, aplicar filtros e rodar testes estatísticos automáticos.")

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
        
        # Mapeamento e padronização automática das colunas (Case-insensitive)
        # Mantemos uma cópia original para exibição se necessário, mas limpamos os nomes das colunas
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Dicionário para tentar encontrar as colunas corretas mesmo com nomes ligeiramente diferentes
        col_map = {
            'idade': [c for c in df.columns if 'idade' in c or 'age' in c or 'dias' in c or 'sem' in c],
            'linhagem': [c for c in df.columns if 'linhagem' in c or 'strain' in c or 'grupo' in c],
            'sexo': [c for c in df.columns if 'sexo' in c or 'sex' in c or 'genero' in c],
            'descarte': [c for c in df.columns if 'descarte' in c or 'tipo' in c or 'destino' in c or 'motivo' in c]
        }
        
        # Validação das colunas obrigatórias
        if not col_map['idade'] or not col_map['linhagem'] or not col_map['sexo']:
            st.error("⚠️ O arquivo precisa conter colunas para: Idade (numérica), Linhagem e Sexo.")
            st.write("Colunas encontradas no seu arquivo:", list(df.columns))
            st.stop()
            
        # Renomeia para um padrão interno estável
        c_idade = col_map['idade'][0]
        c_linha = col_map['linhagem'][0]
        c_sexo = col_map['sexo'][0]
        c_desc = col_map['descarte'][0] if col_map['descarte'] else None
        
        # Limpeza inicial de dados essenciais (remover linhas onde idade, linhagem ou sexo estão vazios)
        df = df.dropna(subset=[c_idade, c_linha, c_sexo])
        df[c_idade] = pd.to_numeric(df[c_idade], errors='coerce')
        df = df.dropna(subset=[c_idade])
        
        # Padronização rigorosa de strings para evitar erros de digitação (Remover espaços e por em Maiúsculo)
        df['sexo_clean'] = df[c_sexo].astype(str).str.strip().str.upper()
        df['linhagem_clean'] = df[c_linha].astype(str).str.strip().str.upper()
        df['linhagem_sexo'] = df['linhagem_clean'] + "(" + df['sexo_clean'] + ")"

        if c_desc:
            # Padroniza também a coluna de descarte para evitar que 'e' e 'E' fiquem separados
            df['descarte_clean'] = df[c_desc].astype(str).str.strip().str.upper()

        # --- PAINEL DE FILTROS NA SIDEBAR ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("2. Filtros do Painel")
        
        # Filtro de Linhagens (Vem com todas selecionadas por padrão)
        todas_linhagens = sorted(df['linhagem_clean'].unique())
        sub_linhagens = st.sidebar.multiselect("Filtrar Linhagens:", todas_linhagens, default=todas_linhagens)
        
        # Filtro de Tipo de Descarte (Se não selecionar nenhum, ele não zera, ele mostra TODOS)
        sub_descartes = []
        if c_desc:
            todos_descartes = sorted(df['descarte_clean'].dropna().unique())
            sub_descartes = st.sidebar.multiselect(
                "Filtrar Tipo de Descarte (Vazio = Todos):", 
                todos_descartes, 
                default=[] # Inicia vazio para não aplicar restrição logo de cara
            )
            
        # Aplicando os filtros de forma segura no DataFrame de análise
        df_filtered = df[df['linhagem_clean'].isin(sub_linhagens)]
        
        # Se o usuário escolheu filtros de descarte, aplicamos. Se deixou vazio, ignora o filtro (mostra tudo).
        if c_desc and len(sub_descartes) > 0:
            df_filtered = df_filtered[df_filtered['descarte_clean'].isin(sub_descartes)]
            
        if df_filtered.empty:
            st.warning("⚠️ Nenhum dado sobrou após aplicar os filtros selecionados. Certifique-se de que a combinação de Linhagem e Descarte selecionada existe na planilha.")
            st.stop()

        # --- VISUALIZAÇÃO PADRÃO (HISTOGRAMA COMPORTADO POR LINHAGEM(SEXO)) ---
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
                labels={c_idade: "Idade (Dias/Semanas)", 'linhagem_sexo': "Linhagem (Sexo)"},
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
                labels={c_idade: "Idade", 'linhagem_sexo': "Linhagem (Sexo)", 'sexo_clean': "Sexo"}
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
        
        # 1. Comparação entre Linhagens
        linhagens_unicas = df_filtered['linhagem_clean'].unique()
        grupos_linhagem = [df_filtered[df_filtered['linhagem_clean'] == lin][c_idade].values for lin in linhagens_unicas]
        
        if len(grupos_linhagem) > 1 and all(len(g) > 2 for g in grupos_linhagem):
            st.markdown("**Comparação de Idade entre Linhagens Diferentes:**")
            
            # Amostragem segura para teste de shapiro
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
        
        # 2. Comparação entre Sexos (M vs F)
        machos = df_filtered[df_filtered['sexo_clean'].isin(['M', 'MACHO', 'MALE'])][c_idade].values
        femeas = df_filtered[df_filtered['sexo_clean'].isin(['F', 'FEMEA', 'FEMALE', 'FE'])][c_idade].values
        
        if len(machos) > 2 and len(femeas) > 2:
            st.markdown("**Comparação de Idade entre Machos vs Fêmeas (Geral):**")
            t_stat, p_val_sex = stats.mannwhitneyu(machos, femeas, alternative='two-sided')
            
            if p_val_sex < 0.05:
                st.error(f"🔴 **Diferença Significativa entre Sexos!** (Mann-Whitney U: p-valor = {p_val_sex:.5f}). Machos e fêmeas possuem idades significativamente diferentes.")
            else:
                st.info(f"🟢 **Sem Diferença Significativa entre Sexos.** (Mann-Whitney U: p-valor = {p_val_sex:.5f}). Não há disparidade estatística nas idades de machos e fêmeas.")

    except Exception as e:
        st.error(f"Erro ao processar e calcular estatísticas do arquivo: {e}")
else:
    st.info("📊 Aguardando o envio do arquivo na barra lateral para renderizar o histograma e filtros padrão.")
