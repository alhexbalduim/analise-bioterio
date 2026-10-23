import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Analisador de Linhagens e Idades", layout="wide")

st.title("🧬 Analisador de Frequência de Linhagens e Bioterio")
st.write("Visualização da distribuição de frequência por intervalos matemáticos de idade versus o combo Linhagem(Sexo).")

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

        # --- LIMPEZA PROFUNDA E CONSTRUÇÃO DOS GRUPOS ---
        df_clean = df.copy()
        df_clean['linhagem_clean'] = df_clean[c_linha].astype(str).str.strip().str.upper()
        df_clean['sexo_clean'] = df_clean[c_sexo].astype(str).str.strip().str.upper()
        
        df_clean[c_idade] = pd.to_numeric(df_clean[c_idade], errors='coerce')
        df_clean = df_clean.dropna(subset=[c_idade])
        
        df_clean = df_clean[~df_clean['linhagem_clean'].isin(['NAN', 'NONE', '', 'NAT'])]
        df_clean = df_clean[~df_clean['sexo_clean'].isin(['NAN', 'NONE', '', 'NAT'])]
        
        # Criando a string combinada padrão solicitada: BALB(M), C57BL/6(F)
        df_clean['linhagem_sexo'] = df_clean['linhagem_clean'] + "(" + df_clean['sexo_clean'] + ")"

        # --- PAINEL DE FILTROS NA SIDEBAR ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("3. Filtros do Painel")
        
        # Filtro de Linhagem Pura
        todas_linhagens = sorted(df_clean['linhagem_clean'].unique())
        sub_linhagens = st.sidebar.multiselect("Filtrar Linhagens:", todas_linhagens, default=todas_linhagens)
        
        # Filtro de Sexo Puro
        todos_sexos = sorted(df_clean['sexo_clean'].unique())
        sub_sexos = st.sidebar.multiselect("Filtrar Sexo:", todos_sexos, default=todos_sexos)
            
        # Aplicação dos filtros selecionados
        df_filtered = df_clean[
            (df_clean['linhagem_clean'].isin(sub_linhagens)) & 
            (df_clean['sexo_clean'].isin(sub_sexos))
        ]
            
        if df_filtered.empty:
            st.error("⚠️ Nenhum dado sobrou para a combinação de filtros selecionada.")
            st.stop()

        # --- CÁLCULO ESTATÍSTICO AUTOMÁTICO DE INTERVALOS ---
        idades_reais = df_filtered[c_idade].values
        
        if len(idades_reais) > 1:
            # Calcula automaticamente as quebras ideais usando a fórmula matemática baseada nos dados filtrados
            quebras_calculadas = np.histogram_bin_edges(idades_reais, bins='auto')
            quebras_calculadas = np.unique(np.round(quebras_calculadas).astype(int))
            if len(quebras_calculadas) < 2:
                quebras_calculadas = np.array([int(idades_reais.min()), int(idades_reais.max() + 1)])
        else:
            quebras_calculadas = np.array([int(idades_reais.min()), int(idades_reais.max() + 1)] if len(idades_reais) == 1 else)

        # Criação dos rótulos matemáticos na notação de intervalo clássica: [inicio ⊢ fim)
        rotulos_matematicos = []
        for i in range(len(quebras_calculadas)-1):
            inicio = quebras_calculadas[i]
            fim = quebras_calculadas[i+1]
            rotulos_matematicos.append(f"[{inicio} ⊢ {fim})")
            
        df_filtered['faixa_idade'] = pd.cut(
            df_filtered[c_idade], 
            bins=quebras_calculadas, 
            labels=rotulos_matematicos, 
            right=False,
            include_lowest=True
        )

        # --- VISUALIZAÇÃO GRÁFICA DA DISTRIBUIÇÃO ---
        st.subheader("📊 Distribuição de Frequência de Animais")
        st.info("📊 **Notação Estatística Utilizada:** Intervalos no formato $[a \vdash b)$, onde o limite inicial faz parte da contagem da barra, mas o limite final pertence à faixa seguinte.")
        
        # Agrupa e conta a quantidade exata de animais por faixa calculada e pelo combo linhagem_sexo
        df_counts = df_filtered.groupby(['faixa_idade', 'linhagem_sexo'], observed=False).size().reset_index(name='Quantidade de Animais')
        
        fig_bar = px.bar(
            df_counts,
            x='faixa_idade',
            y='Quantidade de Animais',
            color='linhagem_sexo',
            barmode='group',
            title="Quantidade de Animais por Intervalos de Frequência Calculados Matemáticos",
            labels={'faixa_idade': 'Intervalos Reais de Idade [Início ⊢ Fim)', 'linhagem_sexo': 'Linhagem (Sexo)'},
            text_auto=True
        )
        fig_bar.update_layout(height=600)
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # --- TABELA DE DISTRIBUIÇÃO DE FREQUÊNCIA ---
        st.subheader("📋 Tabela Resumo de Frequências")
        
        # Exibe os dados contados em formato de planilha limpa para exportação ou conferência
        st.dataframe(
            df_counts[df_counts['Quantidade de Animais'] > 0], 
            use_container_width=True, 
            hide_index=True
        )

    except Exception as e:
        st.error(f"Erro crítico ao processar o arquivo: {e}")
else:
    st.info("📊 Aguardando o envio do arquivo na barra lateral para gerar a distribuição de frequência.")
