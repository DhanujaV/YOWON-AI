import os
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database import RepositoryAnalysis

CACHE_DIR = Path("repository_cache/analysis_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Memory Cache Store
_memory_cache: Dict[str, Dict[str, Any]] = {}
_memory_lock = threading.Lock()

class RepositoryAnalysisCache:
    ANALYSIS_VERSION = "2.0.0"
    ENGINE_VERSION = "2.0.0"

    @classmethod
    def get(cls, commit_sha: str, db: Session) -> Optional[Dict[str, Any]]:
        """Hybrid Cache Lookup: Memory -> Database -> Disk."""
        # 1. Memory Cache Lookup
        with _memory_lock:
            if commit_sha in _memory_cache:
                entry = _memory_cache[commit_sha]
                if cls._is_valid(entry):
                    return entry["data"]

        # 2. Database Cache Lookup (Metadata validation)
        db_analysis = db.query(RepositoryAnalysis).filter(
            RepositoryAnalysis.commit_sha == commit_sha,
            RepositoryAnalysis.analysis_version == cls.ANALYSIS_VERSION,
            RepositoryAnalysis.engine_version == cls.ENGINE_VERSION,
            RepositoryAnalysis.status == "Completed"
        ).first()

        if db_analysis:
            # If DB metadata is valid, try loading the actual artifacts from Disk
            disk_data = cls._load_from_disk(commit_sha)
            if disk_data:
                # Cache to memory for future hits
                with _memory_lock:
                    _memory_cache[commit_sha] = {
                        "analysis_version": cls.ANALYSIS_VERSION,
                        "engine_version": cls.ENGINE_VERSION,
                        "data": disk_data,
                        "expires_at": db_analysis.expires_at.isoformat() if db_analysis.expires_at else None
                    }
                return disk_data

        # 3. Disk Cache Lookup fallback
        disk_data = cls._load_from_disk(commit_sha)
        if disk_data:
            # If we find valid disk artifacts, rebuild DB cache record to stay synced
            try:
                # Add/update DB record
                db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).delete()
                analysis = RepositoryAnalysis(
                    commit_sha=commit_sha,
                    repository_snapshot_id=disk_data.get("repository_snapshot_id", ""),
                    analysis_version=cls.ANALYSIS_VERSION,
                    engine_version=cls.ENGINE_VERSION,
                    status="Completed"
                )
                db.add(analysis)
                db.commit()
            except Exception:
                db.rollback()
            return disk_data

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
                status="Completed",
                expires_at=expires_at
            )
            db.add(analysis)
            db.commit()
        except Exception:
            db.rollback()

    @classmethod
    def get_artifact(cls, commit_sha: str, artifact_name: str) -> Optional[Any]:
        """Loads a single specific analysis artifact JSON file directly from disk (lazy loading)."""
        # Checks if file exists on disk
        folder = CACHE_DIR / commit_sha
        file_path = folder / f"{artifact_name}.json"
        if file_path.exists():
            try:
                return json.loads(file_path.read_text(encoding="utf-8"))
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
        
        artifacts = [
            "repository_tree", "architecture_graph", "dependency_graph", 
            "technology_graph", "call_graph", "metrics", "health", 
            "evidence", "recommendations"
        ]
        
        # Load all separate JSON files into a consolidated dictionary
        data = {}
        for art in artifacts:
            file_path = folder / f"{art}.json"
            if not file_path.exists():
                return None
            try:
                data[art] = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                return None
        return data

    @classmethod
    def _save_to_disk(cls, commit_sha: str, snapshot_id: str, data: Dict[str, Any]) -> None:
        folder = CACHE_DIR / commit_sha
        folder.mkdir(parents=True, exist_ok=True)
        
        # Write separate JSON files
        for key, payload in data.items():
            if isinstance(payload, dict) or isinstance(payload, list):
                # If it's a model or data dict
                file_path = folder / f"{key}.json"
                try:
                    # Write with meta context
                    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                except Exception:
                    pass
