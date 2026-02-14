import sqlite3
from pathlib import Path
from app.utils.logger import log

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "PeopleFlowMonitor.db"


def reset_database(db_path: Path = DB_PATH) -> None:
    """
    Limpa todos os registros da tabela 'counts' e reinicia o contador de IDs.
    """
    if not db_path.exists():
        log.warning(f"O banco de dados não foi encontrado em: {db_path}")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM counts")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='counts'")
            conn.commit()
        log.info(f"Banco de dados '{db_path}' zerado com sucesso.")

    except sqlite3.OperationalError as e:
        log.error(f"Falha crítica ao resetar o banco de dados: {e}")
    except Exception as e:
        log.error(f"Erro inesperado ao resetar o banco de dados: {e}")

if __name__ == "__main__":
    log.info("Iniciando limpeza do banco de dados...")
    reset_database()
