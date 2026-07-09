import uuid
from typing import List, Dict
from intelligence.models import EvidenceRecord, RecommendationRecord
from intelligence.evidence_engine import RULES_METADATA

class RecommendationEngine:
    def generate_recommendations(self, evidence: List[EvidenceRecord]) -> List[RecommendationRecord]:
        """Generates prioritized, traceable recommendations linked directly to code evidence."""
        from intelligence.utils import safe_list
        evidence = safe_list(evidence)
        recommendations = []
        
        # Group evidence by rule_id
        by_rule: Dict[str, List[EvidenceRecord]] = {}
        for ev in evidence:
            if ev.rule_id not in by_rule:
                by_rule[ev.rule_id] = []
            by_rule[ev.rule_id].append(ev)

        for rule_id, ev_list in by_rule.items():
            # Get rule metadata
            meta = RULES_METADATA.get(rule_id, {
                "category": "GENERAL",
                "severity": "LOW",
                "description": "General recommendation",
                "recommendation_template": "Review code patterns for optimal structure.",
                "documentation_reference": ""
            })

            evidence_ids = [hashlib_id(ev) for ev in ev_list]
            affected_files = list({ev.file_path for ev in ev_list})
            
            # Determine maximum severity
            severities = [ev.severity for ev in ev_list]
            max_severity = "INFO"
            for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                if sev in severities:
                    max_severity = sev
                    break

            # Calculate average confidence
            confidences = [ev.confidence for ev in ev_list]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.90

            # Estimate score gain based on severity
            gain_map = {"CRITICAL": 12.5, "HIGH": 7.5, "MEDIUM": 5.0, "LOW": 2.5, "INFO": 1.0}
            score_gain = gain_map.get(max_severity, 1.0)

            # Estimate effort based on category/rule
            effort = "LOW"
            if max_severity in ("CRITICAL", "HIGH") or meta["category"] in ("DATABASE", "ML", "ARCHITECTURE"):
                effort = "MEDIUM"
            if rule_id in ("RULE_SECRET_GENERIC_API_KEY", "RULE_SECRET_PRIVATE_KEY"):
                effort = "HIGH"

            # Create recommendation text
            file_hints = ", ".join(affected_files[:3])
            if len(affected_files) > 3:
                file_hints += f" and {len(affected_files) - 3} other files"

            rec_text = meta["recommendation_template"]
            if affected_files:
                rec_text += f" Affected files: {file_hints}."

            recommendations.append(RecommendationRecord(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, rule_id + "".join(affected_files))),
                evidence_ids=evidence_ids,
                triggered_rule_ids=[rule_id],
                affected_files=affected_files,
                title=meta["description"],
                recommendation=rec_text,
                severity=max_severity,
                expected_score_gain=score_gain,
                confidence=avg_confidence,
                estimated_effort=effort
            ))

        # Sort recommendations by severity priority
        sev_priority = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}
        recommendations.sort(key=lambda r: (-sev_priority.get(r.severity, 0), -r.expected_score_gain))
        return recommendations

def hashlib_id(evidence: EvidenceRecord) -> str:
    # Deterministic ID generation based on file path, rule and lines
    payload = f"{evidence.rule_id}:{evidence.file_path}:{evidence.line_start}:{evidence.line_end}"
    import hashlib
    return hashlib.md5(payload.encode("utf-8")).hexdigest()
