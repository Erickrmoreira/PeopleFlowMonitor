from typing import Dict, Set, Tuple
from time import monotonic

from app.services.storage import StorageService
from app.config.settings import load_zones_config
from app.analytics.statistics import StatsAnalyzer
from app.core.enums import Direction, Position
from app.utils.logger import log


class StreamCounter:
    """
    Gerencia a lógica de contagem de fluxo baseada em zonas virtuais.

    Estratégia:
    - Usa o topo da bounding box para reduzir erros por oclusão.
    - Aplica uma máquina de estados simples para validar cruzamentos.
    """

    def __init__(self) -> None:
        config = load_zones_config()
        zone_data = config.get("counting_line", {})

        self.line_y_ratio: float = zone_data.get("y_ratio", 0.6)
        self.offset: float = zone_data.get("offset", 0.05)
        self.max_inactive_seconds: float = float(zone_data.get("max_inactive_seconds", 10.0))

        stats = StatsAnalyzer()
        report = stats.get_daily_report()

        self.in_count: int = report[Direction.IN.value]
        self.out_count: int = report[Direction.OUT.value]

        self.storage = StorageService()

        self.track_positions: Dict[int, Position] = {}
        self.already_counted: Set[int] = set()
        self.last_seen_at: Dict[int, float] = {}
        self.cleanup_interval_seconds: float = 1.0
        self._last_cleanup_at: float = monotonic()

        log.info(
            f"Contador inicializado | Linha: {self.line_y_ratio} | Offset: {self.offset}"
        )
        log.info(
            f"Estado carregado | IN: {self.in_count} | OUT: {self.out_count}"
        )

    def count(self, results, frame_shape: Tuple[int, int, int]) -> Tuple[int, int]:
        """Processa inferências do detector e atualiza os contadores."""
        h = frame_shape[0]

        line_up = int(h * (self.line_y_ratio - self.offset))
        line_down = int(h * (self.line_y_ratio + self.offset))

        if not results.boxes or results.boxes.id is None:
            self._cleanup_stale_tracks()
            return self.in_count, self.out_count

        boxes_obj = results.boxes
        y_tops = boxes_obj.xyxy[:, 1].cpu().numpy()
        ids = boxes_obj.id.int().cpu().numpy()
        now = monotonic()

        for y_top, obj_id in zip(y_tops, ids):
            obj_id = int(obj_id)
            position = self._get_position(y_top, line_up, line_down)
            self.last_seen_at[obj_id] = now

            if obj_id not in self.track_positions:
                self.track_positions[obj_id] = position
                continue

            prev_pos = self.track_positions[obj_id]

            if obj_id not in self.already_counted:

                if prev_pos in (Position.TOP, Position.MIDDLE) and position == Position.BOTTOM:
                    self._register_event(obj_id, Direction.IN)

                elif prev_pos in (Position.BOTTOM, Position.MIDDLE) and position == Position.TOP:
                    self._register_event(obj_id, Direction.OUT)

            self.track_positions[obj_id] = position

        self._cleanup_stale_tracks()

        return self.in_count, self.out_count

    def _get_position(self, y_top: float, line_up: int, line_down: int) -> Position:
        """Determina a zona espacial do objeto."""
        if y_top < line_up:
            return Position.TOP
        elif y_top > line_down:
            return Position.BOTTOM
        return Position.MIDDLE

    def _register_event(self, obj_id: int, direction: Direction) -> None:
        """Incrementa contadores e persiste o evento."""
        if direction == Direction.IN:
            self.in_count += 1
        else:
            self.out_count += 1

        self.already_counted.add(obj_id)
        self.storage.save_count(direction.value, int(obj_id))

        log.info(f"{direction.value} detectado | ID: {obj_id}")

    def _cleanup_stale_tracks(self) -> None:
        """Remove IDs que ficaram inativos por muito tempo para evitar crescimento de estado."""
        now = monotonic()
        if (now - self._last_cleanup_at) < self.cleanup_interval_seconds:
            return

        stale_ids = [
            obj_id
            for obj_id, last_seen in self.last_seen_at.items()
            if (now - last_seen) > self.max_inactive_seconds
        ]

        for obj_id in stale_ids:
            self.last_seen_at.pop(obj_id, None)
            self.track_positions.pop(obj_id, None)
            self.already_counted.discard(obj_id)

        self._last_cleanup_at = now
