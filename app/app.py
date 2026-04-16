import streamlit as st
import pandas as pd
import cv2
from pathlib import Path
import sys
 
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
 
from process_video import process_video
 
st.set_page_config(page_title="TCC - Analise de Trafego", layout="wide")
 
BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"
GRAPHS_DIR = BASE_DIR / "graphs"
VIDEOS_DIR = BASE_DIR / "videos"
PROCESSED_DIR = BASE_DIR / "processed_videos"
 
RESULTS_DIR.mkdir(exist_ok=True)
GRAPHS_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)
 
if "resultado_processamento" not in st.session_state:
    st.session_state["resultado_processamento"] = None
 
st.title("Sistema de Analise de Fluxo de Trafego")
 
uploaded_file = st.file_uploader("Envie um video", type=["mp4", "mov", "avi", "mkv"])
 
if uploaded_file is not None:
    video_path = VIDEOS_DIR / uploaded_file.name
 
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
 
    st.success("Video enviado com sucesso")
 
    if st.button("Processar video"):
        with st.spinner("Processando video..."):
            st.session_state["resultado_processamento"] = process_video(str(video_path))
        st.success("Processamento concluido")
 
resultado_processamento = st.session_state["resultado_processamento"]
 
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
 
video_processado_file = None
 
if (
    resultado_processamento is not None
    and "video_processado" in resultado_processamento
    and Path(resultado_processamento["video_processado"]).exists()
    and Path(resultado_processamento["video_processado"]).stem == video_base
):
    video_processado_file = Path(resultado_processamento["video_processado"])
else:
    candidate = PROCESSED_DIR / video_base / f"{video_base}.mp4"
    if candidate.exists():
        video_processado_file = candidate
 
df_acumulado = pd.read_csv(csv_acumulado) if csv_acumulado.exists() else None
df_fluxo = pd.read_csv(csv_fluxo) if csv_fluxo.exists() else None
df_tipos = pd.read_csv(csv_tipos) if csv_tipos.exists() else None
 
# --- métricas principais (fonte única: CSVs) ---
total_veiculos = int(df_tipos["quantidade"].sum()) if df_tipos is not None and not df_tipos.empty else 0
tipos_detectados = int(df_tipos["tipo"].nunique()) if df_tipos is not None and not df_tipos.empty else 0
pico_fluxo = int(df_fluxo["veiculos_novos"].max()) if df_fluxo is not None and not df_fluxo.empty else 0
 
duracao_segundos = 0.0
if df_acumulado is not None and not df_acumulado.empty:
    duracao_segundos = float(df_acumulado["tempo_segundos"].max())
 
veiculos_por_minuto = 0.0
if duracao_segundos > 0:
    veiculos_por_minuto = total_veiculos / (duracao_segundos / 60)
 
# --- métricas de vídeo: preferência ao resultado do processamento, fallback ao arquivo ---
if resultado_processamento is not None and Path(resultado_processamento.get("video_processado", "")).stem == video_base:
    fps_val = resultado_processamento.get("fps")
    resolucao_val = resultado_processamento.get("resolucao")
    tamanho_val = resultado_processamento.get("tamanho_mb")
    dispositivo_val = str(resultado_processamento.get("dispositivo", "")).upper()
    tempo_proc_val = resultado_processamento.get("tempo_processamento")
else:
    fps_val = None
    resolucao_val = None
    tamanho_val = None
    dispositivo_val = None
    tempo_proc_val = None
 
    if video_file is not None and video_file.exists():
        cap = cv2.VideoCapture(str(video_file))
        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
 
        fps_val = raw_fps if raw_fps > 0 else None
        tamanho_val = video_file.stat().st_size / (1024 * 1024)
 
        if h >= 2160:
            resolucao_val = "4K"
        elif h >= 1440:
            resolucao_val = "1440p"
        elif h >= 1080:
            resolucao_val = "1080p"
        elif h >= 720:
            resolucao_val = "720p"
        elif h >= 480:
            resolucao_val = "480p"
        elif h > 0:
            resolucao_val = f"{w}x{h}"
 
# --- linha 1: dispositivo, tempo de proc, duração, veículos únicos ---
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Dispositivo", dispositivo_val if dispositivo_val else "—")
col_b.metric("Tempo de processamento (s)", f"{tempo_proc_val:.2f}" if tempo_proc_val is not None else "—")
col_c.metric("Duracao do video (s)", f"{duracao_segundos:.2f}" if duracao_segundos > 0 else "—")
col_d.metric("Veiculos unicos", total_veiculos)
 
# --- linha 2: FPS, tamanho, resolução, veículos/min ---
col_e, col_f, col_g, col_h = st.columns(4)
col_e.metric("FPS", f"{fps_val:.2f}" if fps_val is not None else "—")
col_f.metric("Tamanho do video (MB)", f"{tamanho_val:.1f}" if tamanho_val is not None else "—")
col_g.metric("Resolucao", resolucao_val if resolucao_val else "—")
col_h.metric("Veiculos/min", f"{veiculos_por_minuto:.2f}")
 
if video_processado_file is not None and video_processado_file.exists():
    with st.expander("Ver video processado com deteccoes"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.video(str(video_processado_file))
elif video_file is not None and video_file.exists():
    with st.expander("Ver video original"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.video(str(video_file))
 
tab1, tab2, tab3, tab4 = st.tabs(["Fluxo", "Tipos", "Acumulado", "Arquivos"])
 
with tab1:
    st.subheader("Fluxo por intervalo")
    if graph_fluxo.exists():
        st.image(str(graph_fluxo), width="stretch")
    if df_fluxo is not None:
        st.dataframe(df_fluxo, width="stretch")
        with open(csv_fluxo, "rb") as f:
            st.download_button(
                "Baixar CSV de fluxo",
                data=f,
                file_name=csv_fluxo.name,
                mime="text/csv",
                width="stretch",
            )
 
with tab2:
    st.subheader("Veiculos por tipo")
    if graph_tipos.exists():
        st.image(str(graph_tipos), width="stretch")
    if df_tipos is not None:
        st.dataframe(df_tipos, width="stretch")
        with open(csv_tipos, "rb") as f:
            st.download_button(
                "Baixar CSV de tipos",
                data=f,
                file_name=csv_tipos.name,
                mime="text/csv",
                width="stretch",
            )
 
with tab3:
    st.subheader("Contagem acumulada")
    if df_acumulado is not None:
        st.line_chart(df_acumulado.set_index("tempo_segundos")["veiculos_acumulados"])
        st.dataframe(df_acumulado, width="stretch")
        with open(csv_acumulado, "rb") as f:
            st.download_button(
                "Baixar CSV acumulado",
                data=f,
                file_name=csv_acumulado.name,
                mime="text/csv",
                width="stretch",
            )
 
    if graph_intervalos.exists():
        st.subheader("Distribuicao do tempo entre veiculos")
        st.image(str(graph_intervalos), width="stretch")
 
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
        video_processado_file if video_processado_file is not None else None,
    ]
 
    for arquivo in arquivos:
        if arquivo is not None and Path(arquivo).exists():
            st.write(str(Path(arquivo).relative_to(BASE_DIR)))