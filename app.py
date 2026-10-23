import io
import re
import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Biotério | Distribuição de Idades",
    page_icon="🧬",
    layout="wide",
)

st.title("🧬 Painel do Biotério — Distribuição de Idades")
st.markdown(
    "Analise a distribuição das idades dos animais, com filtros por linhagem e sexo. "
    "A coluna **Idade** é interpretada no formato **semanas,dias** "
    "(ex.: `2,2` = 2 semanas e 2 dias = 16 dias)."
)

ALIASES = {
    "Linhagem": ["linhagem", "strain", "linha"],
    "Data nascimento": [
        "data nascimento", "data de nascimento", "nascimento", "birth date"
    ],
    "Sexo": ["sexo", "sex", "genero", "gênero"],
    "Quantidade": [
        "quantidade", "qtd", "n", "total", "numero de animais", "número de animais"
    ],
    "Destino": [
        "destino", "e z", "eutanásia e zoológico z outros",
        "eutanasia e zoologico z outros", "eutanasia zoologico outros",
        "eutanásia (e) zoológico (z) outros"
    ],
    "Dia do descarte": [
        "dia do descarte", "data do descarte", "data descarte", "descarte"
    ],
    "Observação": ["observacao", "observação", "obs"],
    "Idade": ["idade", "idade em dias", "age", "idade (semanas,dias)"],
}


def normalizar_nome(valor):
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", " ", texto).strip().lower()


def ler_arquivo(arquivo):
    nome = arquivo.name.lower()
    if nome.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(arquivo, engine="openpyxl")
    if nome.endswith(".csv"):
        conteudo = arquivo.getvalue()
        erro = None
        for codificacao in ("utf-8-sig", "cp1252", "latin1"):
            try:
                return pd.read_csv(
                    io.BytesIO(conteudo),
                    sep=None,
                    engine="python",
                    encoding=codificacao,
                )
            except UnicodeDecodeError as exc:
                erro = exc
        raise ValueError(f"Não foi possível ler a codificação do CSV: {erro}")
    raise ValueError("Formato não suportado. Envie um arquivo .xlsx ou .csv.")


def mapear_colunas(df):
    lookup = {normalizar_nome(coluna): coluna for coluna in df.columns}
    renomear = {}
    for nome_padrao, alternativas in ALIASES.items():
        for alternativa in alternativas:
            chave = normalizar_nome(alternativa)
            if chave in lookup:
                renomear[lookup[chave]] = nome_padrao
                break
    return df.rename(columns=renomear)


def idade_semanas_dias_para_dias(valor):
    """
    Interpreta:
      1     -> 1 semana = 7 dias
      0,2   -> 0 semanas e 2 dias = 2 dias
      2,2   -> 2 semanas e 2 dias = 16 dias
      3,1   -> 3 semanas e 1 dia = 22 dias

    Aceita números lidos do Excel como 2.2 ou textos como "2,2".
    O componente de dias precisa estar entre 0 e 6.
    """
    if pd.isna(valor):
        return np.nan

    texto = str(valor).strip()
    if not texto:
        return np.nan

    texto = texto.replace(" ", "")
    correspondencia = re.fullmatch(r"(\d+)(?:[,.](\d+))?", texto)
    if not correspondencia:
        return np.nan

    semanas = int(correspondencia.group(1))
    parte_dias = correspondencia.group(2)

    if parte_dias is None:
        return semanas * 7

    dias = int(parte_dias)
    if dias > 6:
        return np.nan

    return semanas * 7 + dias


def converter_numero(valor):
    if pd.isna(valor):
        return np.nan
    texto = str(valor).strip()
    if not texto:
        return np.nan
    # Aceita quantidade inteira ou decimal em CSV com vírgula decimal.
    texto = texto.replace(",", ".")
    return pd.to_numeric(texto, errors="coerce")


arquivo = st.file_uploader(
    "Selecione a planilha do biotério",
    type=["xlsx", "xlsm", "csv"],
)

if arquivo is None:
    st.info(
        "Envie um arquivo para começar. O painel reconhece os cabeçalhos da amostra, "
        "incluindo Linhagem, Data nascimento, Sexo, Quantidade, "
        "Eutanásia (E) Zoológico (Z) Outros, Dia do descarte e Idade."
    )
    st.stop()

try:
    df_original = ler_arquivo(arquivo)
except Exception as erro:
    st.error(f"Não foi possível ler o arquivo: {erro}")
    st.stop()

if df_original.empty:
    st.error("O arquivo não contém registros.")
    st.stop()

df = mapear_colunas(df_original.copy())

if "Idade" not in df.columns:
    st.error(
        "Não encontrei a coluna **Idade**. Confira o cabeçalho do arquivo. "
        "Colunas identificadas: " + ", ".join(str(c) for c in df_original.columns)
    )
    st.stop()

# Preserva a idade original para auditoria e converte para dias para os cálculos.
df["Idade informada"] = df["Idade"]
df["Idade (dias)"] = df["Idade"].apply(idade_semanas_dias_para_dias)

# Se a idade informada estiver vazia ou inválida, tenta calculá-la a partir das datas.
if "Data nascimento" not in df.columns:
    df["Data nascimento"] = pd.NaT
if "Dia do descarte" not in df.columns:
    df["Dia do descarte"] = pd.NaT

df["Data nascimento"] = pd.to_datetime(
    df["Data nascimento"], errors="coerce", dayfirst=True
)
df["Dia do descarte"] = pd.to_datetime(
    df["Dia do descarte"], errors="coerce", dayfirst=True
)
idade_por_datas = (
    df["Dia do descarte"].dt.normalize() - df["Data nascimento"].dt.normalize()
).dt.days

idade_invalida = df["Idade (dias)"].isna()
df.loc[idade_invalida & idade_por_datas.notna(), "Idade (dias)"] = idade_por_datas[
    idade_invalida & idade_por_datas.notna()
]

if "Linhagem" not in df.columns:
    df["Linhagem"] = "Não informado"
if "Sexo" not in df.columns:
    df["Sexo"] = "Não informado"
if "Destino" not in df.columns:
    df["Destino"] = "Não informado"
if "Observação" not in df.columns:
    df["Observação"] = ""

for coluna in ("Linhagem", "Sexo", "Destino"):
    df[coluna] = (
        df[coluna]
        .fillna("Não informado")
        .astype(str)
        .str.strip()
        .replace("", "Não informado")
    )

df["Linhagem"] = df["Linhagem"].str.upper()
df["Sexo"] = df["Sexo"].str.upper()
df["Destino"] = df["Destino"].str.upper()

if "Quantidade" not in df.columns:
    df["Quantidade"] = 1
else:
    df["Quantidade"] = df["Quantidade"].apply(converter_numero)

qtd_invalida = df["Quantidade"].isna() | (df["Quantidade"] < 0)
idade_invalida = df["Idade (dias)"].isna() | (df["Idade (dias)"] < 0)
linhas_ignoradas = int((qtd_invalida | idade_invalida).sum())
df = df.loc[~(qtd_invalida | idade_invalida)].copy()

if df.empty:
    st.error(
        "Não há linhas válidas para analisar. Confira a coluna Idade. "
        "O formato esperado é semanas,dias (por exemplo, 3,1 = 22 dias). "
        "Se a idade estiver ausente, o painel tenta calculá-la pelas datas de nascimento "
        "e descarte."
    )
    st.stop()

df["Idade (dias)"] = df["Idade (dias)"].astype(int)

# Sinaliza diferenças entre a idade informada e o intervalo calculado pelas datas.
idade_e_datas_validas = idade_por_datas.notna() & df.index.isin(idade_por_datas.index)
# Reindexação explícita mantém alinhamento mesmo após remover linhas inválidas.
datas_validas_df = df[
    df["Data nascimento"].notna() & df["Dia do descarte"].notna()
].copy()
if not datas_validas_df.empty:
    datas_validas_df["Idade pelas datas (dias)"] = (
        datas_validas_df["Dia do descarte"].dt.normalize()
        - datas_validas_df["Data nascimento"].dt.normalize()
    ).dt.days
    discrepancias = int(
        (
            datas_validas_df["Idade pelas datas (dias)"]
            != datas_validas_df["Idade (dias)"]
        ).sum()
    )
else:
    discrepancias = 0

st.sidebar.header("🔎 Filtros")
opcoes_linhagem = sorted(df["Linhagem"].unique().tolist())
opcoes_sexo = sorted(df["Sexo"].unique().tolist())

linhagens_escolhidas = st.sidebar.multiselect(
    "Linhagem", opcoes_linhagem, default=opcoes_linhagem
)
sexos_escolhidos = st.sidebar.multiselect(
    "Sexo", opcoes_sexo, default=opcoes_sexo
)

idade_min_dados = int(df["Idade (dias)"].min())
idade_max_dados = int(df["Idade (dias)"].max())
if idade_min_dados < idade_max_dados:
    faixa_idade = st.sidebar.slider(
        "Faixa de idade (dias)",
        min_value=idade_min_dados,
        max_value=idade_max_dados,
        value=(idade_min_dados, idade_max_dados),
        step=1,
    )
else:
    faixa_idade = (idade_min_dados, idade_max_dados)
    st.sidebar.caption(f"Todos os registros válidos têm {idade_min_dados} dia(s).")

largura_intervalo = st.sidebar.number_input(
    "Largura do intervalo (dias)",
    min_value=1,
    max_value=365,
    value=7,
    step=1,
    help="Use 7 para agrupar por semanas (0–6, 7–13, 14–20 dias etc.).",
)

df_filtrado = df[
    df["Linhagem"].isin(linhagens_escolhidas)
    & df["Sexo"].isin(sexos_escolhidos)
    & df["Idade (dias)"].between(faixa_idade[0], faixa_idade[1], inclusive="both")
].copy()

if df_filtrado.empty:
    st.warning("Nenhum registro corresponde aos filtros selecionados.")
    st.stop()

total_animais = df_filtrado["Quantidade"].sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Animais (soma de Quantidade)", f"{total_animais:,.0f}".replace(",", "."))
k2.metric("Registros/lotes", f"{len(df_filtrado):,}".replace(",", "."))
k3.metric("Menor idade", f"{df_filtrado['Idade (dias)'].min()} dias")
k4.metric("Maior idade", f"{df_filtrado['Idade (dias)'].max()} dias")

if linhas_ignoradas:
    st.warning(
        f"{linhas_ignoradas} linha(s) foram excluídas por idade ou quantidade inválida. "
        "Quando possível, idade ausente foi calculada pelas datas."
    )
if discrepancias:
    st.warning(
        f"{discrepancias} registro(s) têm diferença entre a idade interpretada e "
        "a diferença entre Data nascimento e Dia do descarte. Confira esses dados."
    )

st.divider()
aba_freq, aba_box, aba_dados = st.tabs(
    ["📊 Distribuição de frequência", "📦 Boxplot", "📋 Dados e exportação"]
)

with aba_freq:
    st.subheader("Quantidade de animais por intervalo de idade")
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

with st.expander("ℹ️ Regras de interpretação"):
    st.markdown(
        "- `1` é interpretado como 1 semana (7 dias).\n"
        "- `0,2` é interpretado como 0 semanas e 2 dias.\n"
        "- `2,2` é interpretado como 2 semanas e 2 dias (16 dias).\n"
        "- A idade ausente/inválida é calculada a partir das datas, quando ambas estão disponíveis.\n"
        "- A frequência soma `Quantidade`; o boxplot pondera por `Quantidade` quando possível.\n"
        "- As datas são lidas no padrão dia/mês/ano."
    )
