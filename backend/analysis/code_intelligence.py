"""Deterministic code-aware project intelligence for YOWON AI."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SUPPORTED_SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".java", ".cpp", ".go", ".ipynb"}

FRAMEWORK_PATTERNS: dict[str, tuple[str, ...]] = {
    "FastAPI": ("fastapi", "FastAPI("),
    "Flask": ("flask", "Flask("),
    "Django": ("django",),
    "React": ("react", "from 'react'", 'from "react"', "useState", "useEffect"),
    "Next.js": ("next/", "next.config", "getServerSideProps"),
    "Express": ("require('express')", 'require("express")', "from 'express'", 'from "express"', "express()"),
    "Vue": ("vue", "createApp"),
    "Spring": ("springframework", "@SpringBootApplication"),
    "TensorFlow": ("tensorflow", "keras"),
    "PyTorch": ("torch", "nn.Module"),
    "scikit-learn": ("sklearn", "scikit-learn"),
    "OpenCV": ("cv2", "opencv"),
    "Pandas": ("pandas", "pd."),
    "SQLAlchemy": ("sqlalchemy",),
    "Prisma": ("prisma",),
}

ALGORITHM_PATTERNS: dict[str, tuple[str, ...]] = {
    "XGBoost": ("xgboost", "XGBClassifier", "XGBRegressor"),
    "Random Forest": ("RandomForest", "random forest"),
    "Gradient Boosting": ("GradientBoosting", "gradient boosting"),
    "Neural Network": ("neural network", "nn.Module", "Sequential("),
    "Transformer": ("transformer", "attention", "bert", "gpt"),
    "CNN": ("Conv2D", "Conv1d", "convolution"),
    "Recommendation System": ("recommend", "collaborative", "similarity"),
    "Search/Ranking": ("rank", "tfidf", "bm25", "vector search"),
    "Graph Algorithm": ("networkx", "graph", "shortest_path"),
    "Optimization": ("linear programming", "optimizer", "gradient descent"),
}

PURPOSE_PATTERNS: dict[str, tuple[str, ...]] = {
    "machine learning system": ("predict", "classifier", "model", "training", "dataset"),
    "web application": ("router", "component", "controller", "endpoint", "route"),
    "API service": ("api", "endpoint", "fastapi", "express", "flask"),
    "data pipeline": ("etl", "pipeline", "dataframe", "parquet", "csv"),
    "automation tool": ("cli", "argparse", "automation", "workflow"),
}


def _suffix(path: str) -> str:
    return Path(path.lower()).suffix


def _clean_notebook(content: str) -> str:
    try:
        parsed = json.loads(content)
    except Exception:
        return content
    cells = parsed.get("cells") if isinstance(parsed, dict) else None
    if not isinstance(cells, list):
        return content
    chunks: list[str] = []
    for cell in cells:
        source = cell.get("source") if isinstance(cell, dict) else None
        if isinstance(source, list):
            chunks.append("".join(str(item) for item in source))
        elif isinstance(source, str):
            chunks.append(source)
    return "\n".join(chunks)


def _source_text(source_files: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for item in source_files:
        content = str(item.get("content") or "")
        if _suffix(str(item.get("path") or "")) == ".ipynb":
            content = _clean_notebook(content)
        chunks.append(content[:12000])
    return "\n".join(chunks)


def _matches(text: str, patterns: dict[str, tuple[str, ...]]) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for label, needles in patterns.items():
        if any(needle.lower() in lower for needle in needles):
            found.append(label)
    return found


def read_codebase(ctx: dict[str, Any]) -> dict[str, Any]:
    """Summarize actual implementation evidence from sampled source files."""
    gh = ctx.get("github") or {}
    source_files = [
        item for item in gh.get("source_files") or gh.get("python_files") or []
        if _suffix(str(item.get("path") or "")) in SUPPORTED_SOURCE_EXTENSIONS
    ]
    text = _source_text(source_files)
    files = [str(item.get("path") or "") for item in source_files]
    extensions = Counter(_suffix(path) for path in files)
    lower = text.lower()

    frameworks = _matches(text, FRAMEWORK_PATTERNS)
    algorithms = _matches(text, ALGORITHM_PATTERNS)
    purpose_hits = _matches(text + "\n" + str(ctx.get("description") or "") + "\n" + str(gh.get("readme") or ""), PURPOSE_PATTERNS)

    signals = {
        "rest_api": bool(re.search(r"@(app|router)\.(get|post|put|delete|patch)|app\.(get|post|put|delete)|fetch\(|axios\.", text)),
        "database": any(term in lower for term in ("sqlalchemy", "mongoose", "prisma", "sqlite", "postgres", "mysql", "mongodb", "redis")),
        "authentication": any(term in lower for term in ("jwt", "oauth", "login", "password", "bcrypt", "session", "passport", "auth")),
        "ml_model": any(term in lower for term in ("fit(", "predict(", "torch", "tensorflow", "sklearn", "keras", "xgboost", "model.pkl")),
        "custom_algorithm": bool(re.search(r"\b(class|def|function)\s+\w*(rank|score|detect|classif|predict|optimi|recommend)\w*", text, re.I)),
        "testing": any(term in lower for term in ("pytest", "unittest", "describe(", "it(", "@test", "assert ")),
        "security_implementation": any(term in lower for term in ("sanitize", "csrf", "cors", "encrypt", "hash", "permission", "role")),
        "deployment_pattern": any(term in "\n".join(gh.get("repository_files") or []).lower() for term in ("dockerfile", "render.yaml", "vercel.json", "netlify.toml", ".github/workflows")),
    }

    complexity_points = (
        min(3, len(source_files))
        + min(3, len(frameworks))
        + sum(bool(v) for v in signals.values())
        + min(2, len(algorithms))
    )
    complexity = "High" if complexity_points >= 10 else "Medium" if complexity_points >= 5 else "Low"
    purpose = purpose_hits[0] if purpose_hits else (gh.get("description") or ctx.get("description") or "undetermined project purpose")

    return {
        "purpose": purpose,
        "sampled_files": files[:20],
        "supported_file_count": len(source_files),
        "language_mix": {key or "unknown": value for key, value in extensions.items()},
        "frameworks": frameworks,
        "algorithms": algorithms,
        "signals": signals,
        "complexity": complexity,
        "summary": (
            f"{purpose}; complexity={complexity}; frameworks={', '.join(frameworks) or 'none detected'}; "
            f"algorithms={', '.join(algorithms) or 'none detected'}"
        ),
    }


def summarize_architecture(ctx: dict[str, Any], code_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect architecture layers from code summaries and repository paths."""
    code_summary = code_summary or read_codebase(ctx)
    gh = ctx.get("github") or {}
    files = [str(path).lower() for path in gh.get("repository_files") or []]
    signals = code_summary.get("signals", {})
    frameworks = set(code_summary.get("frameworks") or [])

    layers = {
        "frontend": any(term in " ".join(files) for term in ("src/app", "src/pages", "components", "frontend")) or bool({"React", "Next.js", "Vue"} & frameworks),
        "backend": signals.get("rest_api") or any(term in " ".join(files) for term in ("backend", "server", "api", "routes")),
        "database": bool(signals.get("database")),
        "ml_pipeline": bool(signals.get("ml_model") or code_summary.get("algorithms")),
        "api_layer": bool(signals.get("rest_api")),
        "deployment_layer": bool(signals.get("deployment_pattern")),
        "authentication": bool(signals.get("authentication")),
        "integrations": any(term in _source_text(gh.get("source_files") or []).lower() for term in ("openai", "stripe", "twilio", "sendgrid", "s3", "firebase", "supabase")),
    }
    present = [name.replace("_", " ") for name, enabled in layers.items() if enabled]
    return {
        "layers": layers,
        "summary": "Detected " + (", ".join(present) if present else "limited explicit architecture layers"),
        "complexity": code_summary.get("complexity", "Low"),
    }


def detect_project_type(ctx: dict[str, Any], code_summary: dict[str, Any] | None = None, architecture: dict[str, Any] | None = None) -> dict[str, Any]:
    """Infer project type from code, docs, structure, and description."""
    code_summary = code_summary or read_codebase(ctx)
    architecture = architecture or summarize_architecture(ctx, code_summary)
    gh = ctx.get("github") or {}
    stats = gh.get("repository_statistics") or {}
    text = " ".join([
        str(ctx.get("description") or ""),
        str(gh.get("readme") or ""),
        " ".join(gh.get("topics") or []),
        " ".join(gh.get("repository_files") or []),
        code_summary.get("summary", ""),
    ]).lower()
    layers = architecture.get("layers", {})

    scores = Counter({
        "Hackathon Project": 1,
        "University Project": 0,
        "Research Project": 0,
        "Open Source Project": 0,
        "Startup Product": 0,
        "Enterprise System": 0,
    })
    if any(term in text for term in ("hackathon", "mvp", "prototype", "demo")):
        scores["Hackathon Project"] += 4
    if any(term in text for term in ("university", "course", "assignment", "semester", "student")):
        scores["University Project"] += 4
    if any(term in text for term in ("research", "paper", "experiment", "baseline", "arxiv", "citation", "dataset")) or code_summary.get("algorithms"):
        scores["Research Project"] += 3
    if any(term in text for term in ("license", "contributing", "pull request", "open source")) or int(gh.get("stars") or 0) > 25:
        scores["Open Source Project"] += 3
    if any(term in text for term in ("startup", "customer", "market", "pricing", "revenue", "saas", "product")):
        scores["Startup Product"] += 4
    if any(term in text for term in ("enterprise", "compliance", "production", "kubernetes", "terraform", "rbac")):
        scores["Enterprise System"] += 4
    if layers.get("deployment_layer") and layers.get("authentication") and layers.get("database"):
        scores["Enterprise System"] += 2
    if stats.get("meaningful_files", 0) <= 12 and code_summary.get("complexity") in {"Medium", "High"}:
        scores["Hackathon Project"] += 1

    project_type, points = scores.most_common(1)[0]
    confidence = min(0.95, max(0.35, points / max(1, sum(scores.values())) + 0.35))
    return {
        "project_type": project_type,
        "confidence": round(confidence, 2),
        "signals": dict(scores),
        "justification": f"Detected {project_type} from code/docs/repository signals.",
    }


def extract_technical_evidence(ctx: dict[str, Any], code_summary: dict[str, Any], architecture: dict[str, Any]) -> dict[str, Any]:
    """Convert code and architecture observations into scoring evidence."""
    signals = code_summary.get("signals", {})
    layers = architecture.get("layers", {})
    found: list[str] = []
    missing: list[str] = []

    evidence_map = {
        "Machine learning model": signals.get("ml_model"),
        "Custom algorithm": signals.get("custom_algorithm"),
        "REST API": signals.get("rest_api") or layers.get("api_layer"),
        "Database": signals.get("database") or layers.get("database"),
        "Authentication": signals.get("authentication") or layers.get("authentication"),
        "Docker/deployment": signals.get("deployment_pattern") or layers.get("deployment_layer"),
        "Testing": signals.get("testing"),
        "Security implementation": signals.get("security_implementation"),
    }
    for label, present in evidence_map.items():
        (found if present else missing).append(label)

    return {
        "evidence_found": found,
        "evidence_missing": missing,
        "detected_technologies": sorted(set(code_summary.get("frameworks") or [])),
        "detected_algorithms": sorted(set(code_summary.get("algorithms") or [])),
        "architecture_summary": architecture.get("summary", ""),
    }
