import cv2
from typing import Optional, Tuple

from app.detection.yolo_detector import YOLODetector
from app.tracking.tracker import PersonTracker
from app.analytics.counter import StreamCounter
from app.utils.logger import log


class ProcessingPipeline:
    """
    Pipeline principal de processamento:
    Captura -> Detecção -> Rastreamento -> Contagem -> Exibição
    """

    def __init__(
        self,
        source: str | int,
        detector: Optional[YOLODetector] = None,
        tracker: Optional[PersonTracker] = None,
        counter: Optional[StreamCounter] = None,
    ) -> None:
        log.info("Inicializando Pipeline de Processamento...")
        self.source = source
        self.detector = detector if detector is not None else YOLODetector()
        self.tracker = tracker if tracker is not None else PersonTracker()
        self.counter = counter if counter is not None else StreamCounter()

        self.skip_frames = 2  # Processa IA a cada X frames
        self.win_name = "PeopleFlowMonitor - Monitoramento"
        self.display_width = 640
        self._last_boxes = None
        self._last_ids = None
        self._cached_resize_source: Optional[Tuple[int, int]] = None
        self._cached_resize_target: Optional[Tuple[int, int]] = None

    def run(self) -> None:
        """Executa o pipeline completo de monitoramento."""
        cap = cv2.VideoCapture(self.source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        if not cap.isOpened():
            log.error(f"Não foi possível abrir a fonte de vídeo: {self.source}")
            return
        log.info("Captura de vídeo iniciada com sucesso.")
        try:
            cv2.moveWindow(self.win_name, 40, 40)
        except Exception:
            pass

        frame_nmr = 0
        results: Optional[object] = None
        in_c, out_c = 0, 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                log.warning("Fim do fluxo de vídeo ou falha na leitura do frame.")
                break

            if frame_nmr % self.skip_frames == 0:
                results, in_c, out_c = self._process_frame(frame, results, (in_c, out_c))

            annotated_frame = self._draw_overlay(frame, results, in_c, out_c)
            cv2.imshow(self.win_name, annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                log.info("Tecla 'Q' pressionada. Encerrando monitoramento...")
                break

            frame_nmr += 1

        cap.release()
        cv2.destroyAllWindows()
        log.info(f"Pipeline finalizado. Frames processados: {frame_nmr}")

    def _process_frame(
        self,
        frame,
        last_results,
        last_counts: Tuple[int, int],
    ) -> Tuple[Optional[object], int, int]:
        """
        Atualiza rastreador, realiza detecção e atualiza contadores.
        """
        try:
            results = self.tracker.update(self.detector, frame)
            self._cache_draw_data(results)
            in_c, out_c = self.counter.count(results, frame.shape)
            return results, in_c, out_c
        except Exception as e:
            log.error(f"Erro durante o processamento de IA: {e}")
            return last_results, last_counts[0], last_counts[1]

    def _cache_draw_data(self, results) -> None:
        """Converte boxes/ids uma única vez por ciclo de IA para reduzir custo no draw."""
        self._last_boxes = None
        self._last_ids = None
        if results is None or not results.boxes:
            return

        self._last_boxes = results.boxes.xyxy.cpu().numpy().astype(int)
        if results.boxes.id is not None:
            self._last_ids = results.boxes.id.cpu().numpy().astype(int)

    def _draw_overlay(self, frame, results, in_c: int, out_c: int):
        """
        Adiciona linhas de contagem, painel de estatísticas e retorna frame anotado.
        """
        annotated = frame
        if self._last_boxes is not None:
            for idx, box in enumerate(self._last_boxes):
                x1, y1, x2, y2 = box[:4]
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)
                if self._last_ids is not None and idx < len(self._last_ids):
                    cv2.putText(
                        annotated,
                        f"ID {self._last_ids[idx]}",
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        2,
                    )
        h, w = frame.shape[:2]

        line_up_y = int(h * (self.counter.line_y_ratio - self.counter.offset))
        line_down_y = int(h * (self.counter.line_y_ratio + self.counter.offset))
        cv2.line(annotated, (0, line_up_y), (w, line_up_y), (255, 0, 0), 2)
        cv2.line(annotated, (0, line_down_y), (w, line_down_y), (0, 0, 255), 2)

        # Painel compacto sem caixa de fundo, com sombra para legibilidade
        cv2.putText(annotated, "People Flow", (16, 28), cv2.FONT_HERSHEY_DUPLEX, 0.52, (0, 0, 0), 3)
        cv2.putText(annotated, "People Flow", (16, 28), cv2.FONT_HERSHEY_DUPLEX, 0.52, (235, 235, 235), 1)

        cv2.putText(annotated, f"Entradas (IN): {in_c}", (16, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 3)
        cv2.putText(annotated, f"Entradas (IN): {in_c}", (16, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (30, 220, 80), 1)

        cv2.putText(annotated, f"Saidas (OUT): {out_c}", (16, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 3)
        cv2.putText(annotated, f"Saidas (OUT): {out_c}", (16, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (70, 70, 245), 1)

        display_width = self.display_width
        if w == display_width:
            return annotated
        current_source = (w, h)
        if self._cached_resize_source != current_source or self._cached_resize_target is None:
            aspect_ratio = w / h
            display_height = int(display_width / aspect_ratio)
            self._cached_resize_source = current_source
            self._cached_resize_target = (display_width, display_height)
        return cv2.resize(annotated, self._cached_resize_target)
