from ultralytics import YOLO
from typing import Any
from app.config.settings import MODEL_PATH
from app.utils.logger import log

class YOLODetector:
    """
    Detector de pessoas utilizando o modelo YOLOv8.
    Filtra apenas a classe 'person' (classe 0).
    """


    def __init__(self, model_path: str = MODEL_PATH) -> None:
        self.model_path = model_path
        try:
            self.model = YOLO(model_path)
            log.info(f"YOLO Detector carregado com sucesso: {model_path}")
        except Exception as e:
            log.error(f"Falha ao carregar o modelo YOLO: {e}")
            raise


    def detect(self, frame: Any) -> Any:
        """
        Realiza a detecção de pessoas no frame.

        :param frame: Frame de vídeo (numpy array BGR)
        :return: Resultados da detecção do frame atual
        """
        try:
            results = self.model(frame, classes=[0], verbose=False)
            return results[0]  # Retorna apenas o resultado do frame
        except Exception as e:
            log.error(f"Erro durante detecção no frame: {e}")
            return None


    def track(
        self,
        frame: Any,
        tracker: str = "botsort.yaml",
        conf: float = 0.3,
        iou: float = 0.5,
    ) -> Any:
        """
        Executa tracking de pessoas no frame e retorna o primeiro resultado.
        """
        try:
            results = self.model.track(
                frame,
                persist=True,
                tracker=tracker,
                classes=[0],
                conf=conf,
                iou=iou,
                verbose=False,
            )
            return results[0]
        except Exception as e:
            log.error(f"Erro durante tracking no frame: {e}")
            return None
