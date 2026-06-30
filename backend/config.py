from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"
EXAMPLES_DIR = BASE_DIR / "examples"

for path in [DATA_DIR, OUTPUT_DIR, LOG_DIR, EXAMPLES_DIR]:
    path.mkdir(exist_ok=True)