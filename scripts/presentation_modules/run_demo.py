"""Run a quick demo import and call each module with dummy data."""
from presentation_modules import frontend_module, backend_module, agents_module, integration_module


def make_dummy():
    code_summary = {
        "frameworks": ["FastAPI", "React"],
        "sampled_files": ["backend/main.py", "src/App.tsx", "README.md"],
        "signals": {"rest_api": True, "database": True, "agent_system": True, "vector_database": False},
        "api_examples": ["app.get('/status')"],
        "database_examples": ["create_engine('sqlite:///db.sqlite')"],
        "integration_examples": ["ollama", "github"],
    }
    ctx = {"github": {"repository_files": ["README.md", "backend/main.py", "src/App.tsx"]}}
    numeric_summary = {"overall_score": 78, "agent_scores": {"technical": 80, "security": 70}}
    return code_summary, ctx, numeric_summary


if __name__ == "__main__":
    code_summary, ctx, numeric_summary = make_dummy()
    print('--- Frontend signals ---')
    print(frontend_module.frontend_signals(code_summary, {"layers": {"frontend": True}}))
    print('\n--- Backend signals ---')
    print(backend_module.backend_signals(code_summary))
    print('\n--- Agents signals ---')
    print(agents_module.agent_signals(code_summary))
    print('\nExample agent task:')
    print(agents_module.example_agent_task(numeric_summary))
    print('\n--- Integration signals ---')
    print(integration_module.integration_signals(code_summary, ctx))
