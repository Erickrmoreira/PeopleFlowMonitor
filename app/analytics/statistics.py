import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.config.settings import DB_PATH
from app.utils.logger import log
from app.core.enums import Direction


class StatsAnalyzer:
    """
    Responsável por consultas analíticas do banco de dados.
    Camada isolada para leitura — não grava nada.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        """Cria conexão segura com SQLite."""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            log.critical(f"Falha ao conectar no banco: {e}")
            raise

    def get_daily_report(self) -> Dict[str, int]:
        """
        Retorna total de entradas e saídas do dia atual.

        Returns:
            dict -> {"IN": int, "OUT": int}
        """

        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=1)

        query = """
            SELECT direction, COUNT(*) 
            FROM counts 
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY direction
        """

        report = {
            Direction.IN.value: 0,
            Direction.OUT.value: 0
        }

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    query,
                    (
                        start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    ),
                )
                
                for direction, count in cursor.fetchall():

                    # protege contra valores inesperados no banco
                    if direction in report:
                        report[direction] = count
                    else:
                        log.warning(f"Direção desconhecida encontrada no DB: {direction}")

        except sqlite3.Error as e:
            log.error(f"Erro ao gerar relatório diário: {e}")

        return report

    def get_hourly_peak(self) -> Optional[Dict[str, int]]:
        """
        Retorna a hora com maior volume de eventos no dia atual.

        Returns:
            {"hour": "HH", "count": int}
            ou None se não houver dados
        """

        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=1)

        query = """
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as total
            FROM counts
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY hour
            ORDER BY total DESC
            LIMIT 1
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    query,
                    (
                        start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    ),
                )
                result = cursor.fetchone()

                if not result:
                    return None

                hour, count = result

                log.info(f"Pico de movimento: {hour}h ({count} eventos)")

                return {
                    "hour": hour,
                    "count": count
                }

        except sqlite3.Error as e:
            log.error(f"Erro ao consultar pico horário: {e}")
            return None
