import yaml
from pathlib import Path
from typing import Dict, Any, List

DEFAULT_WEIGHTS = {
    "documentation": {
        "readme_weight": 0.4,
        "comments_weight": 0.4,
        "api_docs_weight": 0.2
    },
    "testing": {
        "test_files_ratio_weight": 0.6,
        "testing_framework_weight": 0.4
    },
    "security": {
        "secrets_weight": 0.4,
        "unsafe_api_weight": 0.3,
        "vulnerabilities_weight": 0.3
    },
    "deployment": {
        "dockerfile_weight": 0.45,
        "docker_compose_weight": 0.25,
        "cicd_weight": 0.30
    },
    "architecture": {
        "folders_ratio_weight": 0.3,
        "separation_of_concerns_weight": 0.7
    },
    "maintainability": {
        "complexity_weight": 0.5,
        "testing_weight": 0.3,
        "documentation_weight": 0.2
    }
}

class HealthEngine:
    def __init__(self):
        self.weights = self._load_weights()

    def _load_weights(self) -> Dict[str, Any]:
        # Path resolution in backend
        config_path = Path(__file__).parent.parent / "config" / "health_weights.yaml"
        if not config_path.exists():
            config_path = Path("config/health_weights.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return DEFAULT_WEIGHTS

    def calculate_health(
        self,
        files: List[str],
        dependencies: Dict[str, str],
        security_findings: List[Dict[str, Any]],
        file_metrics: Dict[str, Dict[str, Any]] # Map of file -> metrics dict
    ) -> Dict[str, Any]:
        """Calculates 6 dimensions of repository health based on YAML configuration."""
        
        # 1. DOCUMENTATION
        has_readme = any(f.lower() == "readme.md" or f.lower().endswith("/readme.md") for f in files)
        readme_score = 100.0 if has_readme else 0.0
        
        # Calculate comment score approximation
        comment_score = 80.0 # Default fallback
        # If we have metrics, use average maintainability or doc features
        doc_files = [f for f in files if f.endswith(".md") or "docs/" in f]
        if len(doc_files) > 1:
            comment_score = min(100.0, 70.0 + len(doc_files) * 10)
        
        has_api_docs = any("swagger" in f.lower() or "openapi" in f.lower() or "api-doc" in f.lower() for f in files)
        api_docs_score = 100.0 if has_api_docs else 50.0

        w_doc = self.weights.get("documentation", DEFAULT_WEIGHTS["documentation"])
        documentation_score = (
            readme_score * w_doc.get("readme_weight", 0.4) +
            comment_score * w_doc.get("comments_weight", 0.4) +
            api_docs_score * w_doc.get("api_docs_weight", 0.2)
        )

        # 2. TESTING
        test_files = [f for f in files if any(t in f.lower() for t in ("test_", "_test", "spec", "__tests__"))]
        total_source_files = len([f for f in files if f.split(".")[-1] in ("py", "js", "ts", "jsx", "tsx", "go", "java")])
        
        ratio_score = 0.0
        if total_source_files > 0:
            ratio_score = min(100.0, (len(test_files) / total_source_files) * 300) # 33% test files is 100 points
        
        test_frameworks = ("pytest", "unittest", "jest", "mocha", "vitest", "testing")
        has_test_framework = any(any(fw in dep.lower() for fw in test_frameworks) for dep in dependencies)
        framework_score = 100.0 if (has_test_framework or len(test_files) > 0) else 0.0

        w_test = self.weights.get("testing", DEFAULT_WEIGHTS["testing"])
        testing_score = (
            ratio_score * w_test.get("test_files_ratio_weight", 0.6) +
            framework_score * w_test.get("testing_framework_weight", 0.4)
        )

        # 3. SECURITY
        secrets_deductions = 0.0
        unsafe_api_deductions = 0.0
        for f in security_findings:
            if f["type"] == "secret_leak":
                secrets_deductions += 30.0 if f["severity"] == "CRITICAL" else 15.0
            elif f["type"] == "unsafe_api":
                unsafe_api_deductions += 10.0

        secrets_score = max(0.0, 100.0 - secrets_deductions)
        unsafe_api_score = max(0.0, 100.0 - unsafe_api_deductions)
        vulnerabilities_score = 100.0 # Placeholder for CVE scans

        w_sec = self.weights.get("security", DEFAULT_WEIGHTS["security"])
        security_score = (
            secrets_score * w_sec.get("secrets_weight", 0.4) +
            unsafe_api_score * w_sec.get("unsafe_api_weight", 0.3) +
            vulnerabilities_score * w_sec.get("vulnerabilities_weight", 0.3)
        )

        # 4. DEPLOYMENT
        has_dockerfile = any("dockerfile" in f.lower() for f in files)
        dockerfile_score = 100.0 if has_dockerfile else 0.0
        
        has_compose = any("docker-compose" in f.lower() for f in files)
        compose_score = 100.0 if has_compose else 0.0
        
        has_cicd = any(".github/workflows/" in f.lower() for f in files)
        cicd_score = 100.0 if has_cicd else 0.0

        w_dep = self.weights.get("deployment", DEFAULT_WEIGHTS["deployment"])
        deployment_score = (
            dockerfile_score * w_dep.get("dockerfile_weight", 0.45) +
            compose_score * w_dep.get("docker_compose_weight", 0.25) +
            cicd_score * w_dep.get("cicd_weight", 0.30)
        )

        # 5. ARCHITECTURE
        # Folders count
        folders = {f.rsplit("/", 1)[0] for f in files if "/" in f}
        folders_ratio = 0.0
        if len(files) > 0:
            folders_ratio = min(100.0, (len(folders) / len(files)) * 300) # Modularity metric

        # Separation of concerns (checking folders named api, routes, db, models, services)
        folder_names = {f.lower().split("/")[-1] for f in folders}
        soc_targets = ("api", "routes", "controllers", "models", "schemas", "database", "services", "utils")
        soc_matched = [t for t in soc_targets if any(t in name for name in folder_names)]
        soc_score = min(100.0, (len(soc_matched) / 4.0) * 100) # Matched 4 major folders is 100

        w_arch = self.weights.get("architecture", DEFAULT_WEIGHTS["architecture"])
        architecture_score = (
            folders_ratio * w_arch.get("folders_ratio_weight", 0.3) +
            soc_score * w_arch.get("separation_of_concerns_weight", 0.7)
        )

        # 6. MAINTAINABILITY
        avg_mi = 85.0
        if file_metrics:
            mi_list = [f.get("complexity", {}).get("maintainability_index", 85.0) for f in file_metrics.values()]
            avg_mi = sum(mi_list) / len(mi_list) if mi_list else 85.0

        w_maint = self.weights.get("maintainability", DEFAULT_WEIGHTS["maintainability"])
        maintainability_score = (
            avg_mi * w_maint.get("complexity_weight", 0.5) +
            testing_score * w_maint.get("testing_weight", 0.3) +
            documentation_score * w_maint.get("documentation_weight", 0.2)
        )

        # Overall Score
        overall = (
            documentation_score +
            testing_score +
            security_score +
            deployment_score +
            architecture_score +
            maintainability_score
        ) / 6.0

        return {
            "overall": round(overall, 1),
            "documentation": round(documentation_score, 1),
            "testing": round(testing_score, 1),
            "security": round(security_score, 1),
            "deployment": round(deployment_score, 1),
            "architecture": round(architecture_score, 1),
            "maintainability": round(maintainability_score, 1),
        }
