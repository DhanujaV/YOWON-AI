import importlib.util
import traceback
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'backend'))
modules = [
    'backend.agents.chief_evaluation_agent',
    'backend.reports.report_generator',
    'backend.tasks.evaluation_tasks',
]

for m in modules:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception:
        print(m, 'ERROR')
        traceback.print_exc()
