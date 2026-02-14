set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "    INICIANDO PeopleFlowMonitor"
echo "=========================================="

# Detecta python do venv
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    echo "[ERRO] Ambiente virtual nao encontrado."
    exit 1
fi

echo "[OK] Python do venv encontrado!"

echo "[1/3] Iniciando API..."
$PYTHON -m uvicorn app.api.main:app &

sleep 2

echo "[2/3] Iniciando IA..."
$PYTHON scripts/run_local.py &

sleep 2

echo "[3/3] Iniciando Dashboard..."
$PYTHON -m streamlit run app/ui/dashboard.py &

trap "kill 0" EXIT
wait
