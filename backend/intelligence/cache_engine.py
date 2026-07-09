import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database import RepositoryAnalysis

import logging

logger = logging.getLogger(__name__)

CACHE_DIR = Path("repository_cache/analysis_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Memory Cache Store
_memory_cache: Dict[str, Dict[str, Any]] = {}
_memory_lock = threading.Lock()

class RepositoryAnalysisCache:
    ANALYSIS_VERSION = "2.0.0"
    ENGINE_VERSION = "2.0.0"

    @classmethod
    def _validate_and_normalize(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates schema types and wraps them in canonical classes (Phase 4 & 6)."""
        from intelligence.canonical_models import (
            CanonicalTreeDict,
            ArchitectureModel,
            TechnologyGraphModel,
            MetricsModel,
            RepositoryIntelligenceSchemaException
        )
        if not data:
            return data

        # 1. Validate repository_tree — keep as plain list so RepositoryIntelligenceResult
        #    Pydantic model wraps it correctly via CanonicalTreeDict validator.
        #    DO NOT wrap here — CanonicalTreeDict(list) converts to {"nodes":[...]} dict
        #    which breaks consumers that do cached_data.get("repository_tree") or []
        tree = data.get("repository_tree")
        if tree is not None:
            # Recover list from CanonicalTreeDict if already wrapped
            if isinstance(tree, CanonicalTreeDict):
                # Extract the underlying list
                tree = list(tree)  # uses __iter__ over self._list
            if not isinstance(tree, list):
                if isinstance(tree, dict) and "nodes" in tree:
                    tree = tree["nodes"]
                elif isinstance(tree, dict) and "tree" in tree:
                    tree = tree["tree"]
                elif isinstance(tree, dict):
                    # Unsupported dict format — reset to empty
                    logger.warning("[CacheEngine][DIAG] repository_tree is dict with unexpected shape: %s", list(tree.keys())[:5])
                    tree = []
                else:
                    raise RepositoryIntelligenceSchemaException(
                        f"repository_tree must be list or dict, got {type(tree)}"
                    )
            data["repository_tree"] = tree  # plain list — Pydantic wraps it in CanonicalTreeDict

        logger.info(
            "[CacheEngine][DIAG] _validate_and_normalize: repository_tree type=%s len=%d",
            type(data.get("repository_tree")).__name__,
            len(data.get("repository_tree") or [])
        )

        # 2. Validate architecture_graph
        arch = data.get("architecture_graph")
        if arch is not None:
            if not isinstance(arch, dict):
                raise RepositoryIntelligenceSchemaException(
                    f"architecture_graph must be dict, got {type(arch)}"
                )
            data["architecture_graph"] = ArchitectureModel(arch)
            assert isinstance(data["architecture_graph"], dict)

        # 3. Validate technology_graph
        tech = data.get("technology_graph")
        if tech is not None:
            if not isinstance(tech, dict):
                raise RepositoryIntelligenceSchemaException(
                    f"technology_graph must be dict, got {type(tech)}"
                )
            data["technology_graph"] = TechnologyGraphModel(tech)
            assert isinstance(data["technology_graph"], dict)

        # 4. Validate evidence
        evidence = data.get("evidence")
        if evidence is not None:
            if not isinstance(evidence, list):
                raise RepositoryIntelligenceSchemaException(
                    f"evidence must be list, got {type(evidence)}"
                )
            assert isinstance(evidence, list)

        # 5. Validate metrics
        metrics = data.get("metrics")
        if metrics is not None:
            if not isinstance(metrics, dict):
                raise RepositoryIntelligenceSchemaException(
                    f"metrics must be dict, got {type(metrics)}"
                )
            data["metrics"] = MetricsModel(metrics)
            assert isinstance(data["metrics"], dict)

        return data


    @classmethod
    def get(cls, commit_sha: str, db: Session) -> Optional[Dict[str, Any]]:
        """Hybrid Cache Lookup: Memory -> Database -> Disk."""
        # 1. Memory Cache Lookup
        with _memory_lock:
            if commit_sha in _memory_cache:
                entry = _memory_cache[commit_sha]
                if cls._is_valid(entry):
                    logger.info(f"[Intel Cache] L1 Memory cache hit for commit={commit_sha}")
                    return cls._validate_and_normalize(entry["data"])

        # 2. Database Cache Lookup (Metadata validation)
        db_analysis = db.query(RepositoryAnalysis).filter(
            RepositoryAnalysis.commit_sha == commit_sha,
            RepositoryAnalysis.analysis_version == cls.ANALYSIS_VERSION,
            RepositoryAnalysis.engine_version == cls.ENGINE_VERSION,
            RepositoryAnalysis.status.in_(["Completed", "COMPLETED"])
        ).first()

        if db_analysis:
            # If DB metadata is valid, try loading the actual artifacts from Disk
            disk_data = cls._load_from_disk(commit_sha)
            if disk_data:
                logger.info(f"[Intel Cache] L2/L3 Hybrid DB+Disk cache hit for commit={commit_sha}")
                # Cache to memory for future hits
                with _memory_lock:
                    _memory_cache[commit_sha] = {
                        "analysis_version": cls.ANALYSIS_VERSION,
                        "engine_version": cls.ENGINE_VERSION,
                        "data": disk_data,
                        "expires_at": db_analysis.expires_at.isoformat() if db_analysis.expires_at else None
                    }
                return cls._validate_and_normalize(disk_data)

        # 3. Disk Cache Lookup fallback
        disk_data = cls._load_from_disk(commit_sha)
        if disk_data:
            logger.info(f"[Intel Cache] L3 Disk cache hit (DB missing/outdated) for commit={commit_sha}. Rebuilding DB cache record.")
            # If we find valid disk artifacts, rebuild DB cache record to stay synced
            try:
                # Add/update DB record
                db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).delete()
                analysis = RepositoryAnalysis(
                    commit_sha=commit_sha,
                    repository_snapshot_id=disk_data.get("repository_snapshot_id", ""),
                    analysis_version=cls.ANALYSIS_VERSION,
                    engine_version=cls.ENGINE_VERSION,
                    status="COMPLETED"
                )
                db.add(analysis)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.exception(f"[Intel Cache] Failed to rebuild database cache record for commit={commit_sha}: {e}")
            return cls._validate_and_normalize(disk_data)

        logger.info(f"[Intel Cache] Cache miss for commit={commit_sha}")
        return None

    @classmethod
    def set(cls, commit_sha: str, snapshot_id: str, data: Dict[str, Any], db: Session) -> None:
        """Saves analysis artifacts to Hybrid Cache (Memory, Database, Disk)."""
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        # 1. Save to Memory
        with _memory_lock:
            _memory_cache[commit_sha] = {
                "analysis_version": cls.ANALYSIS_VERSION,
                "engine_version": cls.ENGINE_VERSION,
                "data": data,
                "expires_at": expires_at.isoformat()
            }

        # 2. Save to Disk (normalized, separate files in folder)
        cls._save_to_disk(commit_sha, snapshot_id, data)

        # 3. Save to Database (Metadata cache entry)
        try:
            # Delete old matches
            db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).delete()
            analysis = RepositoryAnalysis(
                repository_snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                analysis_version=cls.ANALYSIS_VERSION,
                engine_version=cls.ENGINE_VERSION,
                status="COMPLETED",
                expires_at=expires_at
            )
            db.add(analysis)
            db.commit()
            logger.info(f"[Intel Cache] Successfully saved cache record to database for commit={commit_sha}")
        except Exception as e:
            db.rollback()
            logger.exception(f"[Intel Cache] Failed to save cache record to database for commit={commit_sha}: {e}")

    @classmethod
    def set_artifact(cls, commit_sha: str, artifact_name: str, data: Any) -> None:
        """Saves a single specific analysis artifact JSON file directly to disk (lazy writing)."""
        folder = CACHE_DIR / commit_sha
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"{artifact_name}.json"
        try:
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[Intel Cache] Failed to write individual artifact {artifact_name} for commit {commit_sha}: {e}")

    @classmethod
    def get_artifact(cls, commit_sha: str, artifact_name: str) -> Optional[Any]:
        """Loads a single specific analysis artifact JSON file directly from disk (lazy loading)."""
        from intelligence.canonical_models import (
            CanonicalTreeDict,
            ArchitectureModel,
            TechnologyGraphModel,
            MetricsModel,
            RepositoryIntelligenceSchemaException
        )
        # Checks if file exists on disk
        folder = CACHE_DIR / commit_sha
        file_path = folder / f"{artifact_name}.json"
        if file_path.exists():
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                
                # Perform individual validation
                if artifact_name == "repository_tree":
                    if not isinstance(payload, (list, dict)):
                        raise RepositoryIntelligenceSchemaException(
                            f"repository_tree must be list or dict, got {type(payload)}"
                        )
                    # Return plain list — serialize_for_api() handles conversion for frontend
                    if isinstance(payload, dict):
                        payload = payload.get("nodes", payload.get("tree", []))
                    return payload
                elif artifact_name == "architecture_graph":
                    if not isinstance(payload, dict):
                        raise RepositoryIntelligenceSchemaException(
                            f"architecture_graph must be dict, got {type(payload)}"
                        )
                    wrapped = ArchitectureModel(payload)
                    assert isinstance(wrapped, dict)
                    return wrapped
                elif artifact_name == "technology_graph":
                    if not isinstance(payload, dict):
                        raise RepositoryIntelligenceSchemaException(
                            f"technology_graph must be dict, got {type(payload)}"
                        )
                    wrapped = TechnologyGraphModel(payload)
                    assert isinstance(wrapped, dict)
                    return wrapped
                elif artifact_name == "evidence":
                    if not isinstance(payload, list):
                        raise RepositoryIntelligenceSchemaException(
                            f"evidence must be list, got {type(payload)}"
                        )
                    assert isinstance(payload, list)
                    return payload
                elif artifact_name == "metrics":
                    if not isinstance(payload, dict):
                        raise RepositoryIntelligenceSchemaException(
                            f"metrics must be dict, got {type(payload)}"
                        )
                    wrapped = MetricsModel(payload)
                    assert isinstance(wrapped, dict)
                    return wrapped
                return payload
            except RepositoryIntelligenceSchemaException:
                raise
            except Exception:
                return None
        return None

    @classmethod
    def _is_valid(cls, entry: Dict[str, Any]) -> bool:
        if entry.get("analysis_version") != cls.ANALYSIS_VERSION:
            return False
        if entry.get("engine_version") != cls.ENGINE_VERSION:
            return False
        expires_str = entry.get("expires_at")
        if expires_str:
            try:
                expires = datetime.fromisoformat(expires_str)
                if datetime.utcnow() > expires:
                    return False
            except Exception:
                return False
        return True

    @classmethod
    def _load_from_disk(cls, commit_sha: str) -> Optional[Dict[str, Any]]:
        folder = CACHE_DIR / commit_sha
        if not folder.exists():
            return None
        
        # Load and validate metadata.json for version-aware cache invalidation
        meta_file = folder / "metadata.json"
        if not meta_file.exists():
            return None
        try:
            metadata = json.loads(meta_file.read_text(encoding="utf-8"))
            if metadata.get("analysis_version") != cls.ANALYSIS_VERSION:
                return None
            if metadata.get("engine_version") != cls.ENGINE_VERSION:
                return None
            
            # Check prompt template hash registry
            from eval_context.prompt_registry import get_prompt_registry_hash
            current_prompt_hash = get_prompt_registry_hash()
            if metadata.get("prompt_templates_hash") != current_prompt_hash:
                logger.warning(
                    f"[Intel Cache] Invalidating disk cache for commit={commit_sha}: "
                    f"prompt templates hash changed (cached={metadata.get('prompt_templates_hash')}, current={current_prompt_hash})"
                )
                return None
        except Exception:
            return None

        artifacts = [
            "repository_tree", "architecture_graph", "dependency_graph", 
            "technology_graph", "call_graph", "knowledge_graph", "metrics", "health", 
            "evidence", "recommendations", "execution_intelligence",
            "ai_intelligence", "dependency_intelligence", "capabilities",
            "symbols", "file_contents", "detected_technologies", "technology_detections",
            "diagnostics", "quality"
        ]
        
        # Load all separate JSON files into a consolidated dictionary
        data = {}
        for art in artifacts:
            file_path = folder / f"{art}.json"
            if not file_path.exists():
                # Defensively default to empty list or dict based on type
                if art in ("repository_tree", "evidence", "recommendations", "capabilities", "detected_technologies", "technology_detections", "symbols"):
                    data[art] = []
                else:
                    data[art] = {}
                continue
            try:
                data[art] = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                return None

        # Defensively load repository_snapshot_id if it exists
        snap_file = folder / "repository_snapshot_id.json"
        if snap_file.exists():
            try:
                data["repository_snapshot_id"] = json.loads(snap_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return data

    @classmethod
    def _save_to_disk(cls, commit_sha: str, snapshot_id: str, data: Dict[str, Any]) -> None:
        folder = CACHE_DIR / commit_sha
        folder.mkdir(parents=True, exist_ok=True)
        
        # Write separate JSON files
        for key, payload in data.items():
            if isinstance(payload, (dict, list, str)):
                # If it's a model, data dict, list or primitive string
                file_path = folder / f"{key}.json"
                try:
                    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                except Exception:
                    pass

        # Write metadata.json for version-aware cache invalidation
        from eval_context.prompt_registry import get_prompt_registry_hash
        metadata = {
            "analysis_version": cls.ANALYSIS_VERSION,
            "engine_version": cls.ENGINE_VERSION,
            "prompt_templates_hash": get_prompt_registry_hash(),
            "ri_component_versions": {
                "symbol_indexer": "2.1.0",
                "parser_registry": "2.0.5",
                "evidence_engine": "2.2.0",
                "recommendation_engine": "2.0.1",
                "architecture_graph": "2.1.2",
                "dependency_graph": "2.0.0",
                "technology_graph": "2.0.0",
                "call_graph": "2.1.0",
            }
        }
        try:
            (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        except Exception:
            pass

