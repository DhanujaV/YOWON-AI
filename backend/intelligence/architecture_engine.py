from typing import List, Dict, Any
from intelligence.models import EvidenceRecord

class ArchitectureEngine:
    def analyze(self, evidence: List[EvidenceRecord], files: List[str]) -> Dict[str, Any]:
        """Dynamically builds layers and components based on triggered evidence and files."""
        layers = {}
        
        # Deduce layers based on evidence rules
        for ev in evidence:
            rule_id = ev.rule_id
            
            if rule_id == "RULE_FASTAPI_ROUTER":
                if "Backend" not in layers:
                    layers["Backend"] = {"description": "FastAPI Web Server Backend", "files": [], "techs": ["FastAPI"]}
                layers["Backend"]["files"].append(ev.file_path)
            
            elif rule_id == "RULE_SQLALCHEMY_MODEL":
                if "Database" not in layers:
                    layers["Database"] = {"description": "SQLAlchemy Database Layer", "files": [], "techs": ["SQLAlchemy"]}
                layers["Database"]["files"].append(ev.file_path)
            
            elif rule_id == "RULE_AUTH_JWT":
                if "Authentication" not in layers:
                    layers["Authentication"] = {"description": "JWT-based User Authentication", "files": [], "techs": ["JWT"]}
                layers["Authentication"]["files"].append(ev.file_path)
            
            elif rule_id in ("RULE_OLLAMA", "RULE_LANGCHAIN"):
                if "Inference" not in layers:
                    layers["Inference"] = {"description": "LLM Inference Engine", "files": [], "techs": []}
                tech_name = "Ollama" if rule_id == "RULE_OLLAMA" else "LangChain"
                if tech_name not in layers["Inference"]["techs"]:
                    layers["Inference"]["techs"].append(tech_name)
                layers["Inference"]["files"].append(ev.file_path)
                
            elif rule_id == "RULE_VECTOR_DB":
                if "RAG" not in layers:
                    layers["RAG"] = {"description": "Vector Search Database Store", "files": [], "techs": ["Vector DB"]}
                layers["RAG"]["files"].append(ev.file_path)

            elif rule_id == "RULE_CELERY":
                if "Workers" not in layers:
                    layers["Workers"] = {"description": "Background Asynchronous Workers", "files": [], "techs": ["Celery"]}
                layers["Workers"]["files"].append(ev.file_path)

            elif rule_id in ("RULE_DOCKERFILE", "RULE_GITHUB_ACTIONS"):
                if "Deployment" not in layers:
                    layers["Deployment"] = {"description": "Containerized CI/CD & Deployment Configurations", "files": [], "techs": []}
                tech_name = "Docker" if rule_id == "RULE_DOCKERFILE" else "GitHub Actions"
                if tech_name not in layers["Deployment"]["techs"]:
                    layers["Deployment"]["techs"].append(tech_name)
                layers["Deployment"]["files"].append(ev.file_path)

        # Heuristics based on file extensions/paths for Frontend
        frontend_files = [f for f in files if any(f.endswith(ext) for ext in (".jsx", ".tsx", ".html", ".css")) or "frontend/src" in f]
        if frontend_files:
            techs = ["HTML/CSS", "JavaScript"]
            if any(f.endswith(".tsx") for f in frontend_files):
                techs.append("TypeScript")
            if "Frontend" not in layers:
                layers["Frontend"] = {"description": "Client Frontend UI Application", "files": frontend_files[:10], "techs": techs}
            else:
                layers["Frontend"]["files"].extend(frontend_files[:10])

        # Clean duplicates in files
        for key in layers:
            layers[key]["files"] = list(set(layers[key]["files"]))

        return layers
