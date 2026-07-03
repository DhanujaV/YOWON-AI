import os
from typing import List, Dict, Any
from intelligence.models import SymbolRecord, EvidenceRecord

class MetricsEngine:
    def calculate_file_metrics(
        self,
        file_path: str,
        content: str,
        symbols: List[SymbolRecord],
        imports_count: int, # Incoming import reference count
        security_findings: List[Dict[str, Any]],
        has_test_file: bool
    ) -> Dict[str, Any]:
        """Calculates complexity, risk, importance, and coverage metrics for a file."""
        lines = content.splitlines()
        loc = len(lines)
        size_bytes = len(content.encode("utf-8"))
        ext = file_path.split(".")[-1].lower() if "." in file_path else "unknown"

        # 1. Complexity (Cyclomatic, Cognitive, Maintainability)
        from intelligence.parsers.parser_registry import ParserRegistry
        parser = ParserRegistry.get_parser(file_path)
        parser.load(content, file_path)
        
        comp_metrics = {
            "function_count": 0,
            "class_count": 0,
            "cyclomatic_complexity": 1,
            "cognitive_complexity": 0,
            "nesting_depth": 0
        }
        if parser.parse():
            comp_metrics = parser.get_complexity_metrics()

        # Halstead / Maintainability Index
        # Maintainability Index = Max(0, (171 - 5.2 * ln(Volume) - 0.23 * CyclomaticComplexity - 16.2 * ln(LOC)) * 100 / 171)
        # We can simplify:
        cyclo = comp_metrics["cyclomatic_complexity"]
        # Basic maintainability index formula approximation
        if loc > 0:
            import math
            try:
                mi = 171 - 5.2 * math.log(loc * 5) - 0.23 * cyclo - 16.2 * math.log(loc)
                mi = max(0, min(100, (mi * 100) / 171))
            except Exception:
                mi = 80
        else:
            mi = 100

        # 2. Risk Calculation (0-100)
        # Base risk is low
        risk = 10
        
        # Add risk for security findings
        for finding in security_findings:
            if finding["severity"] == "CRITICAL":
                risk += 40
            elif finding["severity"] == "HIGH":
                risk += 25
            elif finding["severity"] == "MEDIUM":
                risk += 15
            else:
                risk += 5

        # Add risk for high complexity
        if cyclo > 20:
            risk += 20
        elif cyclo > 10:
            risk += 10

        # Add risk for very large files
        if loc > 1000:
            risk += 15
        elif loc > 500:
            risk += 8

        risk = min(100, risk)

        # 3. Importance (0-100)
        # Entry points or routing files have high importance
        importance = 10
        name = file_path.split("/")[-1].lower()
        
        # Heuristics for entry points
        if name in ("main.py", "app.py", "index.js", "index.ts", "server.js", "manage.py", "app.tsx"):
            importance = 95
        elif any(term in file_path.lower() for term in ("routes", "controllers", "api", "services")):
            importance = 75
        elif any(term in file_path.lower() for term in ("models", "schemas", "database")):
            importance = 65
        elif any(term in file_path.lower() for term in ("tests", "spec", "docs")):
            importance = 20

        # Boost importance based on incoming imports (centrality)
        importance += min(30, imports_count * 5)
        importance = min(100, importance)

        # 4. Coverage (0-100)
        # If it is a test file, coverage is 100
        # If a test file exists for it, coverage is 90
        # Otherwise, coverage is 0
        if any(term in file_path.lower() for term in ("test_", "_test", "spec", "__tests__")):
            coverage = 100
        elif has_test_file:
            coverage = 90
        else:
            coverage = 0

        # Weighted File Role Classification
        roles = {}
        if name in ("main.py", "app.py", "index.js", "index.ts", "server.js", "manage.py", "app.tsx"):
            roles["Entry Point"] = 0.95
        
        if any(term in file_path.lower() for term in ("routes", "controllers", "api")):
            roles["API"] = 0.85
            roles["Controller"] = 0.70
        
        if any(term in file_path.lower() for term in ("models", "schemas", "database")):
            roles["Database"] = 0.90
            roles["Model"] = 0.80

        if any(term in file_path.lower() for term in ("services", "utils")):
            roles["Service"] = 0.85

        if any(term in file_path.lower() for term in ("tests", "spec", "__tests__")):
            roles["Test"] = 0.99

        if file_path.endswith(".md") or "docs/" in file_path:
            roles["Documentation"] = 0.99

        if "docker" in name or ".github/workflows/" in file_path:
            roles["Deployment"] = 0.99

        if not roles:
            roles["Unknown"] = 1.0

        return {
            "complexity": {
                "cyclomatic_complexity": cyclo,
                "cognitive_complexity": comp_metrics["cognitive_complexity"],
                "maintainability_index": mi,
                "function_count": comp_metrics["function_count"],
                "class_count": comp_metrics["class_count"],
            },
            "risk": risk,
            "importance": importance,
            "coverage": coverage,
            "roles": roles,
            "loc": loc,
            "size_bytes": size_bytes
        }
