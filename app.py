import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Analisador Estatístico", layout="wide")

st.title("📊 Analisador Estatístico Completo")
st.write("Faça o upload do seu arquivo Excel ou CSV para calcular todas as estatísticas possíveis da sua coluna de dados.")

uploaded_file = st.sidebar.file_uploader("Envie seu arquivo (XLSX ou CSV)", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    # Leitura do arquivo
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success("Arquivo carregado com sucesso!")
        
        # Seleção da coluna
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_columns:
            st.error("Nenhuma coluna numérica foi encontrada no arquivo.")
        else:
            selected_col = st.sidebar.selectbox("Selecione a coluna para análise:", numeric_columns)
            
            # Limpeza dos dados (remover NaNs)
            data = df[selected_col].dropna()
            n = len(data)
            
            if n < 2:
                st.warning("A coluna selecionada precisa ter pelo menos 2 valores numéricos válidos.")
            else:
                # --- CÁLCULOS ESTATÍSTICOS ---
                mean = float(np.mean(data))
                std_err = float(stats.sem(data))
                
                # Intervalo de Confiança de 95% (Distribuição t de Student)
                ci_95 = stats.t.interval(0.95, df=n-1, loc=mean, scale=std_err)
                
                # Outras métricas
                median = float(np.median(data))
                
                # Correção segura para a Moda nas versões recentes do SciPy
                mode_res = stats.mode(data, keepdims=True)
                if mode_res.mode.size > 0:
                    mode_val = float(mode_res.mode.flatten()[0])
                else:
                    mode_val = np.nan
                    
                std_dev = float(np.std(data, ddof=1))
                variance = float(np.var(data, ddof=1))
                q25, q75 = np.percentile(data, [25, 75])
                iqr = float(q75 - q25)
                skewness = float(stats.skew(data))
                kurtosis = float(stats.kurtosis(data))
                
                # --- EXIBIÇÃO EM DESTAQUE: INTERVALO DE CONFIANÇA ---
                st.subheader("🎯 Intervalo de Confiança de 95% para a Média")
                col_ic1, col_ic2, col_ic3 = st.columns(3)
                col_ic1.metric("Limite Inferior (95%)", f"{ci_95[0]:.4f}")
                col_ic2.metric("Média Amostral", f"{mean:.4f}")
                col_ic3.metric("Limite Superior (95%)", f"{ci_95[1]:.4f}")
                
                st.info(f"Com 95% de confiança, a verdadeira média da população está contida no intervalo entre **{ci_95[0]:.4f}** e **{ci_95[1]:.4f}**.")
                
                st.markdown("---")
                
                # --- PAINEL DE MÉTRICAS ---
                st.subheader("📈 Resumo Estatístico")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total de Observações (N)", n)
                c2.metric("Média", f"{mean:.4f}")
                c3.metric("Mediana", f"{median:.4f}")
                if not np.isnan(mode_val):
                    c4.metric("Moda", f"{mode_val:.4f}")
                else:
                    c4.metric("Moda", "N/A")
                
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Desvio Padrão", f"{std_dev:.4f}")
                c6.metric("Variância", f"{variance:.4f}")
                c7.metric("Erro Padrão da Média", f"{std_err:.4f}")
                c8.metric("Amplitude Interquartil (IQR)", f"{iqr:.4f}")
                
                c9, c10, c11, c12 = st.columns(4)
                c9.metric("Valor Mínimo", f"{float(np.min(data)):.4f}")
                c10.metric("1º Quartil (25%)", f"{float(q25):.4f}")
                c11.metric("3º Quartil (75%)", f"{float(q75):.4f}")
                c12.metric("Valor Máximo", f"{float(np.max(data)):.4f}")
                
                c13, c14 = st.columns(2)
                c13.metric("Assimetria (Skewness)", f"{skewness:.4f}")
                c14.metric("Curtose (Kurtosis)", f"{kurtosis:.4f}")
                
                st.markdown("---")
                
                # --- VISUALIZAÇÃO GRÁFICA ---
                st.subheader("📊 Visualização dos Dados")
                
                tab1, tab2 = st.tabs(["Histograma com IC 95%", "Boxplot"])
                
                with tab1:
                    # Criando DataFrame temporário limpo para o Plotly Express rodar sem problemas de indexação
                    plot_df = pd.DataFrame({selected_col: data})
                    fig_hist = px.histogram(plot_df, x=selected_col, nbins=30, title="Distribuição dos Dados", marginal="rug")
                    
                    # Correção: Passando os índices corretos [0] e [1] para as linhas verticais
                    fig_hist.add_vline(x=mean, line_dash="solid", line_color="red", annotation_text="Média")
                    fig_hist.add_vline(x=float(ci_95[0]), line_dash="dash", line_color="green", annotation_text="IC 95% Inf")
                    fig_hist.add_vline(x=float(ci_95[1]), line_dash="dash", line_color="green", annotation_text="IC 95% Sup")
                    
                    fig_hist.update_layout(autosize=True, height=500)
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
                with tab2:
                    # Correção: Usando os dados filtrados em um novo DataFrame limpo para evitar conflitos no Streamlit Cloud
                    fig_box = px.box(plot_df, y=selected_col, points="all", title="Boxplot com Detecção de Outliers")
                    fig_box.update_layout(autosize=True, height=500)
                    st.plotly_chart(fig_box, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando o envio do arquivo na barra lateral à esquerda.")
