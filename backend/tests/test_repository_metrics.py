"""Repository metrics classification and ignore rules."""

from tools.github_tool import _build_repository_statistics
from tools.github_tool import _importance_score


def test_repository_metrics_small_repo_counts_meaningful_files():
    metrics = _build_repository_statistics([
        "README.md",
        "src/app.py",
        "tests/test_app.py",
        "requirements.txt",
        ".git/config",
        "node_modules/lib/index.js",
    ]).as_dict()

    assert metrics["total_files"] == 4
    assert metrics["code_files"] == 2
    assert metrics["documentation_files"] == 2
    assert metrics["test_files"] == 1
    assert metrics["configuration_files"] == 1
    assert metrics["meaningful_files"] == 4


def test_repository_metrics_medium_repo_counts_nested_files():
    files = [
        "README.md",
        "docs/report.md",
        "backend/app/main.py",
        "backend/app/routes/recommendations.py",
        "backend/app/models/course.py",
        "frontend/src/App.tsx",
        "tests/test_recommendations.py",
        "data/courses.csv",
        "Dockerfile",
        "pyproject.toml",
    ]
    metrics = _build_repository_statistics(files).as_dict()

    assert metrics["total_files"] == len(files)
    assert metrics["code_files"] == 5
    assert metrics["documentation_files"] == 2
    assert metrics["test_files"] == 1
    assert metrics["deployment_files"] == 1
    assert metrics["data_files"] == 1
    assert metrics["source_modules"] >= 2


def test_repository_metrics_large_repo_ignores_generated_artifacts():
    files = [
        *(f"src/module_{i}/file_{j}.py" for i in range(8) for j in range(4)),
        *(f"tests/module_{i}/test_file_{j}.py" for i in range(8) for j in range(2)),
        "README.md",
        "docs/architecture.md",
        "docker-compose.yml",
        "package.json",
        "data/sample.parquet",
        "dist/assets/bundle.js",
        "build/output/app.min.js",
        "venv/lib/site-packages/pkg.py",
        "__pycache__/app.cpython.pyc",
    ]
    metrics = _build_repository_statistics(list(files)).as_dict()

    assert metrics["total_files"] == 53
    assert metrics["code_files"] == 48
    assert metrics["documentation_files"] == 2
    assert metrics["test_files"] == 16
    assert metrics["deployment_files"] == 1
    assert metrics["data_files"] == 1
    assert metrics["repository_completeness_score"] >= 90


def test_repository_sampling_prioritizes_implementation_paths():
    assert _importance_score("backend/api/routes.py") > _importance_score("docs/overview.md")
    assert _importance_score("main.py") > _importance_score("scripts/helper.py")
    assert _importance_score("frontend/src/App.tsx") > _importance_score("assets/generated.bundle.js")
