from pathlib import Path
import sys

# Adiciona a raiz do projeto ao path para garantir importações relativas
BASE_DIR = Path(__file__).resolve().parent.parent
base_dir_str = str(BASE_DIR)

if base_dir_str not in sys.path:
    sys.path.insert(0, base_dir_str)

from app.core.pipeline import ProcessingPipeline
from app.analytics.statistics import StatsAnalyzer
from app.utils.logger import log

def main(video_source=0):
    """
    Ponto de entrada para execução local do monitoramento por vídeo.
    `video_source` pode ser o ID da webcam (0, 1, ...) ou caminho para arquivo de vídeo.
    """
    log.info("Inicializando PeopleFlowMonitor...")

    try:
        stats = StatsAnalyzer()
        report = stats.get_daily_report()
        log.info("--- [ RESUMO DE HOJE ] ---")
        log.info(f"Entradas (IN): {report['IN']}")
        log.info(f"Saídas  (OUT): {report['OUT']}")
        log.info("--------------------------")
    except Exception as e:
        log.error(f"Falha ao carregar estatísticas iniciais: {e}")

    try:
        pipeline = ProcessingPipeline(source=video_source)
        log.info(f"Acessando fonte de vídeo: {video_source}")
        log.info("Carregando modelos de IA e iniciando captura...")
        pipeline.run()
    except KeyboardInterrupt:
        log.warning("Execução interrompida pelo usuário (Ctrl+C).")
    except Exception as e:
        log.error(f"Falha crítica na execução do pipeline: {e}")
    finally:
        log.info("Sistema encerrado.")

if __name__ == "__main__":
    main()
