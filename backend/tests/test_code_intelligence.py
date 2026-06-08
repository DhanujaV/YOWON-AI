from analysis.code_intelligence import (
    detect_project_type,
    extract_technical_evidence,
    read_codebase,
    summarize_architecture,
)


def test_code_reader_detects_api_ml_database_and_auth():
    ctx = {
        "description": "Insurance fraud detection API",
        "github": {
            "readme": "Fraud detection with model training and API inference.",
            "topics": ["ml", "api"],
            "repository_files": ["app.py", "Dockerfile", "tests/test_app.py"],
            "source_files": [
                {
                    "path": "app.py",
                    "content": """
from fastapi import FastAPI
from sklearn.ensemble import RandomForestClassifier
from sqlalchemy import create_engine
import jwt

app = FastAPI()
model = RandomForestClassifier()
engine = create_engine("sqlite:///app.db")

@app.post("/predict")
def predict(payload):
    token = jwt.decode(payload["token"], "secret", algorithms=["HS256"])
    return {"fraud": model.predict([[1, 2, 3]])[0]}
""",
                },
                {"path": "tests/test_app.py", "content": "def test_predict(): assert True"},
            ],
            "repository_statistics": {"meaningful_files": 3, "code_files": 2},
        },
    }
    code = read_codebase(ctx)
    arch = summarize_architecture(ctx, code)
    evidence = extract_technical_evidence(ctx, code, arch)

    assert "FastAPI" in code["frameworks"]
    assert "Random Forest" in code["algorithms"]
    assert code["signals"]["rest_api"] is True
    assert code["signals"]["database"] is True
    assert code["signals"]["authentication"] is True
    assert "REST API" in evidence["evidence_found"]
    assert "Database" in evidence["evidence_found"]
    assert "Authentication" in evidence["evidence_found"]


def test_project_type_detector_recognizes_research_signal():
    ctx = {
        "description": "Research project with baseline comparison and dataset experiments.",
        "github": {
            "readme": "We report accuracy, baseline, experiment results, and reproducibility.",
            "topics": ["research"],
            "repository_files": ["notebooks/experiment.ipynb"],
            "repository_statistics": {"meaningful_files": 4, "code_files": 1},
            "source_files": [{"path": "notebooks/experiment.ipynb", "content": "{\"cells\": []}"}],
        },
    }
    code = read_codebase(ctx)
    arch = summarize_architecture(ctx, code)
    detected = detect_project_type(ctx, code, arch)
    assert detected["project_type"] == "Research Project"
    assert detected["confidence"] >= 0.5
