import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configura a página do painel
st.set_page_config(page_title="Gestão de Biotério", layout="wide")

st.title("🧬 Analisador de Distribuição e Intervalo de Classes")
st.write("Insira sua planilha Excel ou CSV para calcular as faixas de idades e o perfil de descarte por Linhagem e Sexo.")

# Componente de Upload na Barra Lateral
uploaded_file = st.sidebar.file_uploader("1. Selecione o arquivo de dados", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        # Leitura automatizada do formato
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success("Planilha importada com sucesso!")
        
        # Mapeamento manual de colunas para evitar quebras por nomes diferentes
        colunas_reais = list(df.columns)
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("2. Identifique as Colunas")
        
        def identificar_coluna(termo, lista):
            for i, col in enumerate(lista):
                if termo in str(col).lower():
                    return i
            return 0
            
        col_idade = st.sidebar.selectbox("Coluna de IDADE:", colunas_reais, index=identificar_coluna("idade", colunas_reais))
        col_linha = st.sidebar.selectbox("Coluna de LINHAGEM:", colunas_originais:=colunas_reais, index=identificar_coluna("linhagem", colunas_reais))
        col_sexo = st.sidebar.selectbox("Coluna de SEXO:", colunas_reais, index=identificar_coluna("sexo", colunas_reais))

        # --- PROCESSAMENTO E PADRONIZAÇÃO DOS DADOS ---
        df_processado = df.copy()
        
        # Converte idade para numérico e remove linhas em branco
        df_processado[col_idade] = pd.to_numeric(df_processado[col_idade], errors='coerce')
        df_processado = df_processado.dropna(subset=[col_idade])
        
        # Padroniza textos para maiúsculas e remove espaços vazios nas pontas
        df_processado['Linhagem_Limpa'] = df_processado[col_linha].astype(str).str.strip().str.upper()
        df_processado['Sexo_Limpo'] = df_processado[col_sexo].astype(str).str.strip().str.upper()
        
        # Remove eventuais textos corrompidos de preenchimento vazios
        df_processado = df_processado[~df_processado['Linhagem_Limpa'].isin(['NAN', 'NONE', '', 'NAT'])]
        df_processado = df_processado[~df_processado['Sexo_Limpo'].isin(['NAN', 'NONE', '', 'NAT'])]
        
        # Criação do combo solicitado: ex. BALB(M), C57(F)
        df_processado['Linhagem_Sexo'] = df_processado['Linhagem_Limpa'] + "(" + df_processado['Sexo_Limpo'] + ")"

        # --- INTERFACE DE FILTROS (LINHAGEM E SEXO) ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("3. Filtros de Seleção")
        
        lista_linhagens = sorted(df_processado['Linhagem_Limpa'].unique())
        filtro_linhagem = st.sidebar.multiselect("Filtrar Linhagens:", lista_linhagens, default=lista_linhagens)
        
        lista_sexos = sorted(df_processado['Sexo_Limpo'].unique())
        filtro_sexo = st.sidebar.multiselect("Filtrar Sexo:", lista_sexos, default=lista_sexos)
        
        # Aplicação dos filtros escolhidos pelo usuário
        df_filtrado = df_processado[
            (df_processado['Linhagem_Limpa'].isin(filtro_linhagem)) & 
            (df_processado['Sexo_Limpo'].isin(filtro_sexo))
        ]
        
        if df_filtrado.empty:
            st.warning("⚠️ Nenhum registro corresponde aos filtros selecionados na barra lateral.")
            st.stop()

        # --- CÁLCULO MATEMÁTICO DOS INTERVALOS DE CLASSE ---
        vetor_idades = df_filtrado[col_idade].values
        
        if len(vetor_idades) > 1:
            # np.histogram_bin_edges com 'auto' aplica Sturges e Freedman-Diaconis conforme o volume de dados
            limites_classes = np.histogram_bin_edges(vetor_idades, bins='auto')
            limites_classes = np.unique(np.round(limites_classes).astype(int))
            if len(limites_classes) < 2:
                limites_classes = np.array([int(vetor_idades.min()), int(vetor_idades.max() + 1)])
        else:
            limites_classes = np.array([int(vetor_idades.min()), int(vetor_idades.max() + 1)] if len(vetor_idades) == 1 else)

        # Criação das legendas com notação estatística clássica: [inicio ⊢ fim)
        legendas_classes = []
        for idx in range(len(limites_classes) - 1):
            regiao_inicio = limites_classes[idx]
            regiao_fim = limites_classes[idx + 1]
            legendas_classes.append(f"[{regiao_inicio} ⊢ {regiao_fim})")
            
        df_filtrado['Classe_Idade'] = pd.cut(
            df_filtrado[col_idade], 
            bins=limites_classes, 
            labels=legendas_classes, 
            right=False,
            include_lowest=True
        )

        # --- CONSTRUÇÃO GRÁFICA ---
        st.subheader("📊 Gráficos Analíticos de Distribuição")
        aba_histograma, aba_boxplot = st.tabs(["Intervalo de Classes (Frequência)", "Boxplot de Idades Descartadas"])
        
        with aba_histograma:
            st.info("📊 **Notação Utilizada:** Intervalos no formato $[a \vdash b)$ indicam que o animal com a idade inicial está incluído na barra, mas o número limite final fará parte da barra seguinte.")
            
            # Contagem real por faixa calculada e pelo combo criado
            contagem_classes = df_filtrado.groupby(['Classe_Idade', 'Linhagem_Sexo'], observed=False).size().reset_index(name='Quantidade de Animais')
            
            grafico_barras = px.bar(
                contagem_classes,
                x='Classe_Idade',
                y='Quantidade de Animais',
                color='Linhagem_Sexo',
                barmode='group',
                title="Distribuição de Animais por Intervalo de Classes Calculado",
                labels={'Classe_Idade': 'Intervalos de Classes de Idade', 'Quantidade de Animais': 'Contagem de Animais'},
                text_auto=True
            )
            grafico_barras.update_layout(height=550)
            st.plotly_chart(grafico_barras, use_container_width=True)
            
        with aba_boxplot:
            grafico_box = px.box(
                df_filtrado,
                x='Linhagem_Sexo',
                y=col_idade,
                color='Sexo_Limpo',
                points="all",
                title="Boxplot de Distribuição de Idades por Grupo com Outliers",
                labels={col_idade: 'Idade Observada', 'Linhagem_Sexo': 'Agrupamento Linhagem(Sexo)'}
            )
            grafico_box.update_layout(height=550)
            st.plotly_chart(grafico_box, use_container_width=True)

        # --- EXIBIÇÃO DA TABELA CONSOLIDADA ---
        st.markdown("---")
        st.subheader("📋 Tabela Consolidada de Frequências")
        st.dataframe(
            contagem_classes[contagem_classes['Quantidade de Animais'] > 0],
            use_container_width=True,
            hide_index=True
        )

    except Exception as erro:
        st.error(f"Não foi possível processar a estrutura do arquivo. Detalhes: {erro}")
else:
    st.info("📊 Aguardando o upload de um arquivo de dados (.xlsx, .xls ou .csv) na barra lateral esquerda para gerar as análises.")
