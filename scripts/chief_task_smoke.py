from pathlib import Path

from importlib.util import spec_from_file_location, module_from_spec

root = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('evaluation_tasks', str(root / 'backend' / 'tasks' / 'evaluation_tasks.py'))
mod = module_from_spec(spec)
spec.loader.exec_module(mod)

engine_out = 'TECHNICAL SCORE: 70\nSECURITY SCORE: 60\nTOP 3 STRENGTHS: x,y,z'
innov_out = 'INNOVATION SCORE: 80\nSCALABILITY SCORE: 50\nTOP COMPETITORS: a,b,c'
ppt_out = 'PRESENTATION SCORE: 65\nTOP 3 STRENGTHS: p,q,r'
risk_out = 'IMPACT SCORE: 75\nTOP 5 RISKS: r1,r2'

task = mod.create_chief_evaluation_task(None, engine_out, innov_out, ppt_out, risk_out)
print('EXPECTED OUTPUT:', task.expected_output)
print('\n--- DESCRIPTION ---\n')
print(task.description)
