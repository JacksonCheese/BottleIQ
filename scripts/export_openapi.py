"""Run with: uv run --project apps/api python scripts/export_openapi.py"""
import json
from pathlib import Path
from bottleiq.main import app

output = Path(__file__).resolve().parents[1] / "packages/shared/openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(output)
