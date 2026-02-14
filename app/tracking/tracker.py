from typing import Any, Protocol

class DetectorProtocol(Protocol):
    def track(self, frame: Any, tracker: str, conf: float, iou: float) -> Any:
        ...


class PersonTracker:
    """
    Rastreador de pessoas usando BOT-SORT com YOLO.
    Mantém IDs consistentes mesmo em sobreposição ou movimento rápido.
    """


    def __init__(self, tracker_config: str = "botsort.yaml", conf: float = 0.3, iou: float = 0.5):
        """
        :param tracker_config: Arquivo de configuração do BOT-SORT
        :param conf: Limite mínimo de confiança para considerar detecção
        :param iou: Limite de IOU para associar boxes entre frames
        """
        self.tracker_type = tracker_config
        self.conf = conf
        self.iou = iou


    def update(self, detector: DetectorProtocol, frame: Any) -> Any:
        """
        Atualiza o rastreamento de pessoas no frame atual.

        :param detector: Instância compatível com DetectorProtocol
        :param frame: Frame atual (BGR)
        :return: Resultados do rastreador para o frame
        """
        result = detector.track(
            frame,
            tracker=self.tracker_type,
            conf=self.conf,      # Confiança mínima
            iou=self.iou,        # Sobreposição mínima para manter IDs
        )
        return result
