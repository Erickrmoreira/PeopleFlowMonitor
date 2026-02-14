import logging
import sys

class SafeStreamHandler(logging.StreamHandler):
    """Stream handler que evita falha de encoding em consoles legados."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            encoding = getattr(stream, "encoding", None) or "utf-8"
            safe_msg = msg.encode(encoding, errors="replace").decode(encoding, errors="replace")
            stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logger(name: str = "PeopleFlowMonitor", level: int = logging.INFO) -> logging.Logger:
    """
    Configura e retorna um logger de alto nível para todo o projeto.
    
    :param name: Nome do logger (pode ser usado para módulos específicos)
    :param level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :return: Instância configurada do logger
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        # Formato uniforme: [DATA HORA] [NÍVEL] Mensagem
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Possível extensão futura: FileHandler, RotatingFileHandler etc.

    return logger

log = setup_logger()
