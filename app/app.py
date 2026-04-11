import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from process_video import process_video

st.set_page_config(page_title="TCC - Analise de Trafego", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"
GRAPHS_DIR = BASE_DIR / "graphs"
VIDEOS_DIR = BASE_DIR / "videos"

st.title("Sistema de Analise de Fluxo de Trafego")

uploaded_file = st.file_uploader("Envie um video", type=["mp4", "mov", "avi", "mkv"])

if uploaded_file is not None:
    video_path = VIDEOS_DIR / uploaded_file.name

    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("Video enviado com sucesso")

    if st.button("Processar video"):
        with st.spinner("Processando video..."):
            process_video(str(video_path))
        st.success("Processamento concluido")

bases = sorted(
    {
        file.stem.replace("_fluxo", "").replace("_tipos", "")
        for file in RESULTS_DIR.glob("*.csv")
    }
)

if not bases:
    st.warning("Nenhum resultado encontrado na pasta results.")
    st.stop()

video_base = st.selectbox("Selecione um video analisado", bases)

csv_acumulado = RESULTS_DIR / f"{video_base}.csv"
csv_fluxo = RESULTS_DIR / f"{video_base}_fluxo.csv"
csv_tipos = RESULTS_DIR / f"{video_base}_tipos.csv"

graph_fluxo = GRAPHS_DIR / f"{video_base}_fluxo.png"
graph_tipos = GRAPHS_DIR / f"{video_base}_tipos.png"
graph_intervalos = GRAPHS_DIR / f"{video_base}_intervalos.png"

video_file = None
for ext in [".mp4", ".mov", ".avi", ".mkv"]:
    candidate = VIDEOS_DIR / f"{video_base}{ext}"
    if candidate.exists():
        video_file = candidate
        break

df_acumulado = pd.read_csv(csv_acumulado) if csv_acumulado.exists() else None
df_fluxo = pd.read_csv(csv_fluxo) if csv_fluxo.exists() else None
df_tipos = pd.read_csv(csv_tipos) if csv_tipos.exists() else None

total_veiculos = int(df_tipos["quantidade"].sum()) if df_tipos is not None and not df_tipos.empty else 0
tipos_detectados = int(df_tipos["tipo"].nunique()) if df_tipos is not None and not df_tipos.empty else 0
pico_fluxo = int(df_fluxo["veiculos_novos"].max()) if df_fluxo is not None and not df_fluxo.empty else 0

duracao_segundos = 0.0
if df_acumulado is not None and not df_acumulado.empty:
    duracao_segundos = float(df_acumulado["tempo_segundos"].max())

veiculos_por_minuto = 0.0
if duracao_segundos > 0:
    veiculos_por_minuto = total_veiculos / (duracao_segundos / 60)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Veiculos unicos", total_veiculos)
col2.metric("Tipos detectados", tipos_detectados)
col3.metric("Pico de fluxo", pico_fluxo)
col4.metric("Veiculos/min", f"{veiculos_por_minuto:.2f}")

if video_file is not None:
    with st.expander("Ver video analisado"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.video(str(video_file))

tab1, tab2, tab3, tab4 = st.tabs(["Fluxo", "Tipos", "Acumulado", "Arquivos"])

with tab1:
    st.subheader("Fluxo por intervalo")
    if graph_fluxo.exists():
        st.image(str(graph_fluxo), use_container_width=True)
    if df_fluxo is not None:
        st.dataframe(df_fluxo, use_container_width=True)
        with open(csv_fluxo, "rb") as f:
            st.download_button(
                "Baixar CSV de fluxo",
                data=f,
                file_name=csv_fluxo.name,
                mime="text/csv",
                use_container_width=True,
            )

with tab2:
    st.subheader("Veiculos por tipo")
    if graph_tipos.exists():
        st.image(str(graph_tipos), use_container_width=True)
    if df_tipos is not None:
        st.dataframe(df_tipos, use_container_width=True)
        with open(csv_tipos, "rb") as f:
            st.download_button(
                "Baixar CSV de tipos",
                data=f,
                file_name=csv_tipos.name,
                mime="text/csv",
                use_container_width=True,
            )

with tab3:
    st.subheader("Contagem acumulada")
    if df_acumulado is not None:
        st.line_chart(df_acumulado.set_index("tempo_segundos")["veiculos_acumulados"])
        st.dataframe(df_acumulado, use_container_width=True)
        with open(csv_acumulado, "rb") as f:
            st.download_button(
                "Baixar CSV acumulado",
                data=f,
                file_name=csv_acumulado.name,
                mime="text/csv",
                use_container_width=True,
            )

    if graph_intervalos.exists():
        st.subheader("Distribuicao do tempo entre veiculos")
        st.image(str(graph_intervalos), use_container_width=True)

with tab4:
    st.subheader("Arquivos encontrados")
    arquivos = [
        csv_acumulado,
        csv_fluxo,
        csv_tipos,
        graph_fluxo,
        graph_tipos,
        graph_intervalos,
        video_file if video_file is not None else None,
    ]

    for arquivo in arquivos:
        if arquivo is not None and Path(arquivo).exists():
            st.write(str(Path(arquivo).relative_to(BASE_DIR)))