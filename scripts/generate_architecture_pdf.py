from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.units import mm

output_path = "./artifacts/architecture_flow.pdf"

styles = getSampleStyleSheet()
H1 = styles['Heading1']
H2 = styles['Heading2']
N = styles['Normal']
CODE = ParagraphStyle('Code', fontName='Courier', fontSize=8, leading=10)

content = []

def add_heading(text):
    content.append(Paragraph(text, H1))
    content.append(Spacer(1, 6))

def add_subheading(text):
    content.append(Paragraph(text, H2))
    content.append(Spacer(1, 4))

def add_para(text):
    content.append(Paragraph(text, N))
    content.append(Spacer(1, 4))

def add_code(text):
    # Preformatted preserves whitespace
    content.append(Preformatted(text, CODE))
    content.append(Spacer(1, 6))

add_heading('Project Sentinel — Architecture & Code Map')
add_para('This document maps the evaluation pipeline from a GitHub link through extraction, analysis, specialist agents, deterministic scoring, narrative generation, and final report generation. Each step lists the implementing file and a short code snippet.')

steps = [
    ("1) API: accept GitHub link (FastAPI endpoint)", 'backend/main.py',
    """safe_github_url = validate_github_url(github_url)
project = Project(..., github_url=safe_github_url, ...)
db.add(project); db.commit()
return JSONResponse({"project_id": project_id, ...})"""),
]

# The full list of items (shortened for readability)
items = [
    ("API: accept GitHub link", 'backend/main.py',
     "safe_github_url = validate_github_url(github_url)\nproject = Project(..., github_url=safe_github_url, ...)\ndb.add(project); db.commit()\nreturn JSONResponse({\"project_id\": project_id, ...})"),
    ("Trigger evaluation (background)", 'backend/main.py',
     "background_tasks.add_task(_run_evaluation_background, project_id)\n# background worker: results = run_evaluation(project_id, ctx, ctx_text)"),
    ("Fetch + extract repository data", 'backend/tools/github_tool.py',
     "def extract_github_data(github_url: str) -> dict[str, Any]:\n    repo_name = _repo_name_from_url(github_url)\n    gh = _github_client()\n    repo = gh.get_repo(repo_name)\n    result['readme'] = _safe_decode(repo.get_readme())[:6000]\n    file_paths = _tree_file_paths(repo)"),
    ("Build project context & code intelligence", 'backend/tools/parser.py',
     "futures['github'] = executor.submit(extract_github_data, github_url)\nctx['code_reader'] = read_codebase(ctx)\nctx['architecture'] = summarize_architecture(ctx, ctx['code_reader'])"),
    ("Static security scanning", 'backend/tools/parser.py -> tools/security_tool.py',
     "security_future = executor.submit(run_security_analysis, python_files, dep_files, source_files)\nctx['security'] = security_future.result()"),
    ("Build deterministic brief", 'backend/eval_context/brief_builder.py',
     "brief: EvaluationBrief = build_brief(ctx)\nbrief_text = truncate_brief(brief.to_text())"),
    ("Slice context per-agent", 'backend/eval_context/context_slicer.py',
     "def slice_context_for_agent(ctx, agent):\n    if agent == 'technical': brief_parts.append(_gh_excerpt(ctx, readme_limit=1000))\n    return truncate_text(text, MAX_AGENT_DIGEST_CHARS, label=f'digest:{agent}')"),
    ("Specialist task factories", 'backend/tasks/evaluation_tasks.py',
     "def create_technical_task(agent, brief, digest):\n    return Task(description=f'Brief:\n{brief}\nEvidence:\n{digest}\nReturn JSON: {\"technical_score\": <int 0-100>, ... }')"),
    ("Specialist agent factory", 'backend/agents/specialist_agents.py',
     "def _agent(...):\n    return Agent(..., llm=get_llm('specialist'), max_iter=1, max_execution_time=600)") ,
    ("Run specialists and parse JSON", 'backend/crew/crew.py',
     "raw = invoke_with_retry(lambda: _execute(), fallback_fn=_execute_fallback)\nreport, parse_source = parse_agent_json(raw, model_cls, FALLBACKS[name])"),
    ("Deterministic scoring in Python", 'backend/scoring/score_engine.py',
     "overall = round(sum(agent_map[k] * WEIGHTS.get(k,0) for k in agent_map))\nif overall >= 85: verdict='APPROVE' ... return {'overall_score': overall, 'verdict': verdict, 'risk_level': risk, 'agent_scores': agent_map}") ,
    ("Narrative agent (LLM) - narrative-only", 'backend/agents/narrative_agent.py & backend/tasks/evaluation_tasks.py',
     "create_narrative_task(agent, numeric_summary, key_findings) -> Task(description='Numeric summary:\n{...}\nKey findings...')"),
    ("Invoke narrative & fallback", 'backend/crew/crew.py',
     "narrative_raw = _run_agent_llm(agent=narrative_agent, task=narrative_task, ...)\nif not narrative_raw.strip(): narrative_raw = json.dumps({'executive_summary': 'Evaluation completed successfully. Narrative generation unavailable.'})"),
    ("Report generation (PDF)", 'backend/reports/report_generator.py',
     "path = generate_report(project.name, project.id, results)")
]

for title, path, snippet in items:
    add_subheading(f"{title}")
    add_para(f"File: {path}")
    add_code(snippet)

add_heading('Notes')
add_para('PDF generated programmatically from repository files. If ReportLab is not installed, install via pip install reportlab.')

# build PDF

doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
doc.build(content)
print(f"Wrote: {output_path}")
