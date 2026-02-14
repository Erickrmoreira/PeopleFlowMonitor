import sqlite3
from pathlib import Path
from app.utils.logger import log

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "PeopleFlowMonitor.db"


def init_db(db_path: Path = DB_PATH) -> None:
    """
    Inicializa o banco de dados e cria a tabela 'counts' se não existir.
    
    Estrutura da tabela:
        - id: PRIMARY KEY autoincrement
        - direction: 'IN' ou 'OUT'
        - timestamp: Data e hora do evento
        - object_id: ID do objeto rastreado
    """
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"Inicializando banco de dados em: {db_path}")

        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    direction TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    object_id INTEGER NOT NULL
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_counts_timestamp
                ON counts(timestamp)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_counts_direction_timestamp
                ON counts(direction, timestamp)
            ''')
            conn.commit()

        log.info("Tabela 'counts' e índices criados/verificados com sucesso.")

    except sqlite3.Error as e:
        log.error(f"Erro de banco de dados: {e}")
    except Exception as e:
        log.error(f"Erro inesperado ao inicializar o banco: {e}")

if __name__ == "__main__":
    init_db()
