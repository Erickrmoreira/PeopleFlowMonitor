from pathlib import Path
import cv2
import yaml
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
base_dir_str = str(BASE_DIR)
if base_dir_str not in sys.path:
    sys.path.insert(0, base_dir_str)

from app.utils.logger import log
from app.config.settings import load_zones_config

CONFIG_PATH = BASE_DIR / "app" / "config" / "zones.yaml"


class Calibrator:
    """Ferramenta de calibração visual da linha de contagem do PeopleFlowMonitor."""

    def __init__(self):
        self.config = load_zones_config()
        self.y_ratio = self.config.get('counting_line', {}).get('y_ratio', 0.5)
        self.temp_y = self.y_ratio
        self.frame = None

    def mouse_callback(self, event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN and self.frame is not None:
            self.temp_y = y / self.frame.shape[0]
            log.info(f"Nova posição capturada: {self.temp_y:.3f}")

    def save_config(self):
        """Salva a nova configuração no YAML."""
        try:
            self.config.setdefault('counting_line', {})['y_ratio'] = round(self.temp_y, 3)
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f)
            log.info(f"Configuração salva com sucesso em: {CONFIG_PATH}")
        except Exception as e:
            log.error(f"Falha ao salvar configuração: {e}")

    def run(self, camera_index=0):
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            log.error("Não foi possível acessar a câmera para calibração.")
            return

        cv2.namedWindow("Calibrador PeopleFlowMonitor")
        cv2.setMouseCallback("Calibrador PeopleFlowMonitor", self.mouse_callback)

        log.info("--- MODO DE CALIBRAÇÃO INICIADO ---")
        log.info("Clique na imagem para definir altura | S: Salvar | Q: Sair")

        offset_ratio = self.config.get('counting_line', {}).get('offset', 0.02)

        while True:
            ret, self.frame = cap.read()
            if not ret:
                log.warning("Falha ao capturar frame da câmera.")
                break

            h, w = self.frame.shape[:2]
            y_pos = int(h * self.temp_y)
            offset_px = int(h * offset_ratio)

            # Desenha linhas de pré-visualização
            cv2.line(self.frame, (0, y_pos - offset_px), (w, y_pos - offset_px), (255, 0, 0), 2)
            cv2.line(self.frame, (0, y_pos + offset_px), (w, y_pos + offset_px), (0, 0, 255), 2)

            cv2.putText(self.frame, f"Ratio atual: {self.temp_y:.3f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(self.frame, "S: Salvar | Q: Sair", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow("Calibrador PeopleFlowMonitor", self.frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                self.save_config()
                break
            elif key == ord('q'):
                log.info("Saindo sem salvar alterações.")
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    Calibrator().run()
