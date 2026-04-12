import csv
import cv2
import imageio
import matplotlib.pyplot as plt
from pathlib import Path
from ultralytics import YOLO
import torch
import time

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"
GRAPHS_DIR = BASE_DIR / "graphs"
MODELS_DIR = BASE_DIR / "models"
PROCESSED_DIR = BASE_DIR / "processed_videos"

def process_video(video_path):
    video_path = Path(video_path)
    video_name = video_path.name
    video_stem = video_path.stem

    RESULTS_DIR.mkdir(exist_ok=True)
    GRAPHS_DIR.mkdir(exist_ok=True)
    PROCESSED_DIR.mkdir(exist_ok=True)

    csv_path = RESULTS_DIR / f"{video_stem}.csv"
    fluxo_csv_path = RESULTS_DIR / f"{video_stem}_fluxo.csv"
    tipos_csv_path = RESULTS_DIR / f"{video_stem}_tipos.csv"

    fluxo_graph_path = GRAPHS_DIR / f"{video_stem}_fluxo.png"
    tipos_graph_path = GRAPHS_DIR / f"{video_stem}_tipos.png"
    intervalos_graph_path = GRAPHS_DIR / f"{video_stem}_intervalos.png"

    processed_video_dir = PROCESSED_DIR / video_stem
    processed_video_dir.mkdir(exist_ok=True)
    processed_video_path = processed_video_dir / f"{video_stem}.mp4"

    model = YOLO(str(MODELS_DIR / "yolo11n.pt"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    start_time = time.time()

    video = cv2.VideoCapture(str(video_path))
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()

    if fps <= 0:
        fps = 30

    duracao_estimada = total_frames / fps if fps > 0 else 0

    if duracao_estimada <= 30:
        intervalo_segundos = 5
    elif duracao_estimada <= 120:
        intervalo_segundos = 10
    elif duracao_estimada <= 300:
        intervalo_segundos = 15
    elif duracao_estimada <= 900:
        intervalo_segundos = 30
    else:
        intervalo_segundos = 60

    # ← MUDOU: imageio no lugar do VideoWriter do OpenCV
    writer = imageio.get_writer(
        str(processed_video_path),
        fps=fps,
        codec="libx264",
        quality=5,
        macro_block_size=None
    )

    results = model.track(
        str(video_path),
        classes=[2, 3, 5, 7],
        conf=0.6,
        save=False,
        stream=True,
        persist=True
    )

    total = 0
    frame_num = 0

    ids_unicos = set()
    ids_por_tipo = {}
    primeiro_tempo_por_id = {}
    fluxo_por_intervalo = {}
    dados = []

    for r in results:
        frame_num += 1
        tempo = frame_num / fps if fps > 0 else 0
        total += len(r.boxes)

        annotated_frame = r.plot()
        # ← MUDOU: converte BGR→RGB antes de salvar
        writer.append_data(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))

        if r.boxes.id is not None:
            for cls, obj_id in zip(r.boxes.cls.tolist(), r.boxes.id.tolist()):
                obj_id = int(obj_id)
                nome = r.names[int(cls)]

                ids_unicos.add(obj_id)

                if nome not in ids_por_tipo:
                    ids_por_tipo[nome] = set()
                ids_por_tipo[nome].add(obj_id)

                if obj_id not in primeiro_tempo_por_id:
                    primeiro_tempo_por_id[obj_id] = tempo
                    inicio = int((tempo // intervalo_segundos) * intervalo_segundos)

                    if inicio not in fluxo_por_intervalo:
                        fluxo_por_intervalo[inicio] = 0

                    fluxo_por_intervalo[inicio] += 1

        dados.append([tempo, len(ids_unicos)])

    # ← MUDOU: close() no lugar de release()
    writer.close()

    duracao_video = frame_num / fps if fps > 0 else 0
    veiculos_por_minuto = len(ids_unicos) / (duracao_video / 60) if duracao_video > 0 else 0

    tempos_ordenados = sorted(primeiro_tempo_por_id.values())
    intervalos = []

    for i in range(1, len(tempos_ordenados)):
        intervalos.append(tempos_ordenados[i] - tempos_ordenados[i - 1])

    with open(csv_path, "w", newline="") as f:
        writer_csv = csv.writer(f)
        writer_csv.writerow(["tempo_segundos", "veiculos_acumulados"])
        writer_csv.writerows(dados)

    with open(fluxo_csv_path, "w", newline="") as f:
        writer_csv = csv.writer(f)
        writer_csv.writerow(["inicio_segundos", "fim_segundos", "veiculos_novos"])
        for inicio in sorted(fluxo_por_intervalo.keys()):
            writer_csv.writerow([inicio, inicio + intervalo_segundos, fluxo_por_intervalo[inicio]])

    with open(tipos_csv_path, "w", newline="") as f:
        writer_csv = csv.writer(f)
        writer_csv.writerow(["tipo", "quantidade"])
        for nome, conjunto in ids_por_tipo.items():
            writer_csv.writerow([nome, len(conjunto)])

    intervalos_x = []
    valores_y = []

    for inicio in sorted(fluxo_por_intervalo.keys()):
        intervalos_x.append(f"{inicio}-{inicio + intervalo_segundos}s")
        valores_y.append(fluxo_por_intervalo[inicio])

    plt.figure(figsize=(12, 5))
    plt.bar(intervalos_x, valores_y)
    plt.xlabel("Intervalo de tempo")
    plt.ylabel("Veiculos novos")
    plt.title("Fluxo de veiculos por intervalo")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(fluxo_graph_path)
    plt.close()

    tipos = []
    quantidades = []

    for nome, conjunto in ids_por_tipo.items():
        tipos.append(nome)
        quantidades.append(len(conjunto))

    plt.figure(figsize=(8, 5))
    plt.bar(tipos, quantidades)
    plt.xlabel("Tipo de veiculo")
    plt.ylabel("Quantidade")
    plt.title("Veiculos unicos por tipo")
    plt.tight_layout()
    plt.savefig(tipos_graph_path)
    plt.close()

    if len(intervalos) > 0:
        plt.figure(figsize=(10, 5))
        plt.hist(intervalos, bins=10)
        plt.xlabel("Tempo entre veiculos (s)")
        plt.ylabel("Frequencia")
        plt.title("Distribuicao do tempo entre aparicao de veiculos")
        plt.tight_layout()
        plt.savefig(intervalos_graph_path)
        plt.close()

    end_time = time.time()
    tempo_processamento = end_time - start_time

    return {
        "total_deteccoes": total,
        "veiculos_unicos": len(ids_unicos),
        "duracao_video": duracao_video,
        "veiculos_por_minuto": veiculos_por_minuto,
        "intervalo_segundos": intervalo_segundos,
        "tempo_processamento": tempo_processamento,
        "dispositivo": device,
        "video_processado": str(processed_video_path)
    }