import sqlite3
import os
import atexit
from datetime import datetime
from time import monotonic
from threading import Lock, Event, Thread
import time
from collections import deque
from typing import Optional
from app.utils.logger import log

class StorageService:
    """
    Serviço responsável por persistência de contagens no SQLite.
    Cria automaticamente a tabela 'counts' caso não exista.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = db_path or os.path.join(base_dir, "data", "PeopleFlowMonitor.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = Lock()
        self._conn_lock = Lock()
        self._buffer = deque()
        self._batch_size = 20
        self._flush_interval_seconds = 1.0
        self._max_buffer_size = 5000
        self._dropped_events = 0
        self._enqueued_events = 0
        self._flushed_events = 0
        self._flush_success_count = 0
        self._flush_failure_count = 0
        self._last_flush_batch_size = 0
        self._last_flush_error: Optional[str] = None
        self._max_retries = 3
        self._retry_backoff_seconds = 0.05
        self._last_flush = monotonic()
        self._started_at = datetime.now()
        self._last_flush_at: Optional[str] = None
        self._metrics_log_interval_seconds = 60.0
        self._last_metrics_log = monotonic()
        self._stop_event = Event()
        self._flush_thread: Optional[Thread] = None
        self._closed = False
        self._connect()
        self._create_table()
        self._start_flush_worker()
        atexit.register(self.close)

    def _connect(self) -> None:
        """Abre conexão persistente com SQLite e ativa WAL."""
        self._conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

    def _start_flush_worker(self) -> None:
        """Inicia worker leve para flush periódico independente de novas gravações."""
        self._flush_thread = Thread(target=self._flush_worker_loop, daemon=True)
        self._flush_thread.start()

    def _flush_worker_loop(self) -> None:
        while not self._stop_event.wait(self._flush_interval_seconds):
            self._flush_if_needed(force=True)
            self._maybe_log_metrics()

    def _create_table(self) -> None:
        """Cria a tabela counts se não existir."""
        try:
            assert self._conn is not None
            with self._conn_lock:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS counts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        direction TEXT NOT NULL,
                        object_id INTEGER NOT NULL
                    )
                """)
                self._conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_counts_timestamp
                    ON counts(timestamp)
                """)
                self._conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_counts_direction_timestamp
                    ON counts(direction, timestamp)
                """)
                self._conn.commit()
            log.info(f"Banco de dados inicializado com sucesso: {self.db_path}")
        except Exception as e:
            log.error(f"Falha ao criar/verificar tabela counts: {e}")
            raise

    def save_count(self, direction: str, object_id: int) -> None:
        """
        Persiste um evento de contagem no banco.

        :param direction: Direção do evento ('IN' ou 'OUT')
        :param object_id: ID do objeto rastreado
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._lock:
                self._enqueue_event_locked((timestamp, direction, object_id))
                should_flush = len(self._buffer) >= self._batch_size
            if should_flush:
                self._flush_if_needed()
        except sqlite3.OperationalError as e:
            log.error(f"ERRO OPERACIONAL: Banco bloqueado ou inacessível: {e}")
        except Exception as e:
            log.error(f"ERRO AO SALVAR NO BANCO: {e}")

    def _enqueue_event_locked(self, event: tuple[str, str, int]) -> None:
        """Enfileira evento com limite de memória para evitar crescimento indefinido."""
        if len(self._buffer) >= self._max_buffer_size:
            self._buffer.popleft()  # drop oldest
            self._dropped_events += 1
            if self._dropped_events % 100 == 0:
                log.warning(f"Eventos descartados por buffer cheio: {self._dropped_events}")
        self._buffer.append(event)
        self._enqueued_events += 1

    def _dequeue_batch(self, force: bool) -> list[tuple[str, str, int]]:
        with self._lock:
            if not self._buffer:
                return []

            elapsed = monotonic() - self._last_flush
            if not force and len(self._buffer) < self._batch_size and elapsed < self._flush_interval_seconds:
                return []

            batch_size = len(self._buffer) if force else min(len(self._buffer), self._batch_size)
            return [self._buffer.popleft() for _ in range(batch_size)]

    def _requeue_front(self, pending: list[tuple[str, str, int]]) -> None:
        with self._lock:
            for event in reversed(pending):
                if len(self._buffer) >= self._max_buffer_size:
                    self._buffer.pop()  # drop newest already queued to preserve pending
                    self._dropped_events += 1
                self._buffer.appendleft(event)

    def _flush_if_needed(self, force: bool = False) -> None:
        """Persiste buffer por tamanho de lote, intervalo, ou flush forçado."""
        pending = self._dequeue_batch(force=force)
        if not pending:
            return

        assert self._conn is not None

        for attempt in range(1, self._max_retries + 1):
            try:
                with self._conn_lock:
                    self._conn.executemany(
                        "INSERT INTO counts (timestamp, direction, object_id) VALUES (?, ?, ?)",
                        pending,
                    )
                    self._conn.commit()
                self._last_flush = monotonic()
                self._last_flush_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._last_flush_batch_size = len(pending)
                self._flushed_events += len(pending)
                self._flush_success_count += 1
                self._last_flush_error = None
                log.debug(f"?? {len(pending)} evento(s) persistido(s) com sucesso.")
                return
            except sqlite3.OperationalError as e:
                if attempt >= self._max_retries:
                    log.error(f"ERRO OPERACIONAL no flush em lote (tentativa final): {e}")
                    self._flush_failure_count += 1
                    self._last_flush_error = str(e)
                    self._requeue_front(pending)
                    return
                time.sleep(self._retry_backoff_seconds * attempt)
            except Exception as e:
                log.error(f"ERRO no flush em lote: {e}")
                self._flush_failure_count += 1
                self._last_flush_error = str(e)
                self._requeue_front(pending)
                return

    def _maybe_log_metrics(self) -> None:
        now = monotonic()
        if (now - self._last_metrics_log) < self._metrics_log_interval_seconds:
            return

        metrics = self.get_metrics()
        log.info(
            f"Storage metrics | buffer={metrics['buffer_size']}/{metrics['max_buffer_size']} "
            f"dropped={metrics['dropped_events']} flushed={metrics['flushed_events']} "
            f"flush_ok={metrics['flush_success_count']} flush_fail={metrics['flush_failure_count']}"
        )
        self._last_metrics_log = now

    def get_metrics(self) -> dict:
        """Retorna métricas operacionais do buffer e flush para monitoramento."""
        with self._lock:
            return {
                "db_path": self.db_path,
                "started_at": self._started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "buffer_size": len(self._buffer),
                "max_buffer_size": self._max_buffer_size,
                "dropped_events": self._dropped_events,
                "enqueued_events": self._enqueued_events,
                "flushed_events": self._flushed_events,
                "flush_success_count": self._flush_success_count,
                "flush_failure_count": self._flush_failure_count,
                "last_flush_batch_size": self._last_flush_batch_size,
                "last_flush_monotonic": self._last_flush,
                "last_flush_at": self._last_flush_at,
                "last_flush_error": self._last_flush_error,
                "is_closed": self._closed,
            }

    def close(self) -> None:
        """Garante persistência final e fechamento seguro da conexão."""
        if self._closed:
            return

        self._closed = True
        self._stop_event.set()
        if self._flush_thread is not None and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=2.0)

        while True:
            with self._lock:
                if not self._buffer:
                    break
            self._flush_if_needed(force=True)
        if self._conn is not None:
            with self._conn_lock:
                self._conn.close()
                self._conn = None

