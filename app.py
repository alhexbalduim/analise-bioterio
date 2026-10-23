st.caption(
        "O eixo X contém intervalos em dias; o eixo Y soma a coluna Quantidade. "
        "O filtro de linhagem e sexo é aplicado antes da contagem."
    )

    largura = int(largura_intervalo)
    idade_min_sel = int(df_filtrado["Idade (dias)"].min())
    idade_max_sel = int(df_filtrado["Idade (dias)"].max())
    inicio = (idade_min_sel // largura) * largura
    fim_exclusivo = (idade_max_sel // largura + 1) * largura
    bordas = np.arange(inicio, fim_exclusivo + 1, largura)
    if len(bordas) < 2:
        bordas = np.array([inicio, inicio + largura])

    rotulos = [
        f"{int(bordas[i])}–{int(bordas[i + 1] - 1)} dias"
        for i in range(len(bordas) - 1)
    ]
    df_filtrado["Intervalo de idade"] = pd.cut(
        df_filtrado["Idade (dias)"],
        bins=bordas,
        labels=rotulos,
        right=False,
        include_lowest=True,
    )

    frequencia = (
        df_filtrado.groupby("Intervalo de idade", observed=False)["Quantidade"]
        .sum()
        .reindex(rotulos, fill_value=0)
        .rename("Quantidade de animais")
        .reset_index()
    )

    fig_freq = px.bar(
        frequencia,
        x="Intervalo de idade",
        y="Quantidade de animais",
        text="Quantidade de animais",
        title="Distribuição de frequência das idades",
    )
    fig_freq.update_traces(textposition="outside", cliponaxis=False)
    fig_freq.update_layout(
        xaxis_title="Intervalos de idade",
        yaxis_title="Quantidade de animais",
        xaxis={"categoryorder": "array", "categoryarray": rotulos},
        margin={"t": 70, "b": 70},
    )
    st.plotly_chart(fig_freq, use_container_width=True)
    st.dataframe(frequencia, use_container_width=True, hide_index=True)

with aba_box:
    st.subheader("Boxplot das idades por linhagem e sexo")
    st.caption(
        "O boxplot considera os animais individualmente, repetindo a idade de cada lote "
        "de acordo com Quantidade quando o total é administrável. Assim, lotes maiores "
        "contribuem proporcionalmente para a distribuição."
    )

    quantidade = df_filtrado["Quantidade"].to_numpy(dtype=float)
    quantidades_inteiras = np.all(np.isclose(quantidade, np.round(quantidade)))
    total_expandido = int(np.round(quantidade).sum()) if quantidades_inteiras else 0

    if quantidades_inteiras and 0 < total_expandido <= 50000:
        indices = np.repeat(
            np.arange(len(df_filtrado)),
            np.round(quantidade).astype(int),
        )
        fonte_box = df_filtrado.reset_index(drop=True).iloc[indices].copy()
        rotulo_box = "Distribuição por animal (ponderada por Quantidade)"
    else:
        fonte_box = df_filtrado.copy()
        if not quantidades_inteiras:
            st.warning(
                "Há quantidades fracionárias. Para evitar distorção, o boxplot mostra "
                "cada registro uma vez, sem ponderar pela Quantidade."
            )
        elif total_expandido > 50000:
            st.warning(
                "O total ultrapassa 50.000 animais; para evitar consumo excessivo de "
                "memória, o boxplot mostra cada registro uma vez, sem ponderar pela Quantidade."
            )
        rotulo_box = "Distribuição por registro/lote (não ponderada)"

    fig_box = px.box(
        fonte_box,
        x="Linhagem",
        y="Idade (dias)",
        color="Sexo",
        points="all",
        hover_data=["Destino"],
        title="Distribuição das idades por linhagem e sexo",
    )
    fig_box.update_layout(
        xaxis_title="Linhagem",
        yaxis_title="Idade (dias)",
        boxmode="group",
    )
    st.plotly_chart(fig_box, use_container_width=True)
    st.caption(rotulo_box)

with aba_dados:
    st.subheader("Dados incluídos na análise")
    colunas = [
        coluna for coluna in [
            "Linhagem", "Data nascimento", "Sexo", "Quantidade", "Destino",
            "Dia do descarte", "Observação", "Idade informada", "Idade (dias)",
        ]
        if coluna in df_filtrado.columns
    ]
    st.dataframe(
        df_filtrado[colunas].sort_values(["Linhagem", "Idade (dias)", "Sexo"]),
        use_container_width=True,
        hide_index=True,
    )

    saida = io.BytesIO()
    with pd.ExcelWriter(saida, engine="xlsxwriter") as writer:
        df_filtrado[colunas].to_excel(writer, sheet_name="Dados filtrados", index=False)
        frequencia.to_excel(writer, sheet_name="Frequencia por idade", index=False)

    st.download_button(
        "📥 Baixar dados e frequência em Excel",
        data=saida.getvalue(),
        file_name="relatorio_bioterio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
