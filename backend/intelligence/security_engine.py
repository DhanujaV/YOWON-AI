import re
from typing import List, Dict, Any
from intelligence.parsers.parser_registry import ParserRegistry

# Common regex patterns for secrets
SECRET_PATTERNS = {
    "generic_api_key": re.compile(r'(?:key|api|token|secret|passwd|password)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.\~]{16,})["\']', re.IGNORECASE),
    "private_key": re.compile(r'-----BEGIN\s+(?:RSA|EC|DSA|GPG|OPENSSH)\s+PRIVATE\s+KEY-----'),
    "db_url": re.compile(r'mongodb(?:\+srv)?://|postgres://|mysql://|sqlite://'),
    "hardcoded_jwt": re.compile(r'eyJhbGciOi[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9_\-\.]+')
}

class SecurityEngine:
    def __init__(self):
        self.findings: Dict[str, List[Dict[str, Any]]] = {}

    def scan_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Scan file content for secrets and unsafe APIs, caching the results."""
        self.remove_file(file_path)

        file_findings = []
        lines = content.splitlines()

        # 1. Secret Scanning
        for key, pattern in SECRET_PATTERNS.items():
            for line_no, line in enumerate(lines, 1):
                # Skip comments where templates or instructions exist
                if line.strip().startswith(("#", "//", "/*", "*")):
                    continue
                for match in pattern.finditer(line):
                    matched_val = match.group(0)
                    # Filter template strings
                    if any(term in matched_val for term in ("${", "{{", "env.", "process.env", "os.environ")):
                        continue
                    
                    file_findings.append({
                        "type": "secret_leak",
                        "rule_id": f"RULE_SECRET_{key.upper()}",
                        "file_path": file_path,
                        "line_start": line_no,
                        "line_end": line_no,
                        "column_start": match.start(),
                        "column_end": match.end(),
                        "description": f"Potential leak of secret: {key.replace('_', ' ')}",
                        "severity": "CRITICAL" if key == "private_key" else "HIGH",
                        "confidence": 0.85
                    })

        # 2. Language-Specific Unsafe API Usage
        parser = ParserRegistry.get_parser(file_path)
        parser.load(content, file_path)
        if parser.parse():
            parser_unsafe = parser.scan_unsafe_apis()
            for item in parser_unsafe:
                file_findings.append({
                    "type": "unsafe_api",
                    "rule_id": f"RULE_UNSAFE_API_{item['api'].replace('.', '_').upper()}",
                    "file_path": file_path,
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                    "column_start": item["column_start"],
                    "column_end": item["column_end"],
                    "description": item["description"],
                    "severity": "HIGH",
                    "confidence": 0.95
                })

        self.findings[file_path] = file_findings
        return file_findings

    def remove_file(self, file_path: str) -> None:
        """Clear findings for a file (useful for incremental changes)."""
        self.findings.pop(file_path, None)

    def get_findings_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        return self.findings.get(file_path, [])

    def get_all_findings(self) -> List[Dict[str, Any]]:
        all_findings = []
        for file_path, list_findings in self.findings.items():
            all_findings.extend(list_findings)
        return all_findings
