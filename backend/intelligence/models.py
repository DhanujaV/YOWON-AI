from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class RepositoryTreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "dir"
    language: Optional[str] = None
    extension: Optional[str] = None
    size: int = 0
    loc: int = 0
    sha256: Optional[str] = None
    roles: Dict[str, float] = Field(default_factory=dict)  # Weighted classification: e.g. {"Entry Point": 0.98}
    generated: bool = False
    ignored: bool = False
    children: Optional[List[RepositoryTreeNode]] = None

# Support recursive type reference in Pydantic v2
RepositoryTreeNode.model_rebuild()

class SymbolRecord(BaseModel):
    name: str
    type: str  # "class" | "function" | "method" | "interface" | "route" | "decorator" | "model"
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    relationships: List[Dict[str, Any]] = Field(default_factory=list)

class EvidenceRecord(BaseModel):
    rule_id: str
    parser: str
    language: str
    symbol_name: Optional[str] = None
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    matched_code_hash: str
    confidence: float
    severity: str  # "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

class TechnologyRecord(BaseModel):
    name: str
    version: Optional[str] = None
    confidence: float
    evidence_sources: List[str] = Field(default_factory=list)

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecommendationRecord(BaseModel):
    id: str
    evidence_ids: List[str] = Field(default_factory=list)
    triggered_rule_ids: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    title: str
    recommendation: str
    severity: str
    expected_score_gain: float
    confidence: float
    estimated_effort: str  # "LOW" | "MEDIUM" | "HIGH"
