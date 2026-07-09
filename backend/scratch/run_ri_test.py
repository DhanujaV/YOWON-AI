"""
Scratch script to run repository intelligence on a real snapshot from the database,
and trace the repository_tree lifecycle logs.
"""
import sys
import os
import logging

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

sys.path.append(os.path.abspath("."))

from database import SessionLocal, RepositorySnapshot, Evaluation
from intelligence.intelligence_service import run_repository_intelligence
from eval_context.evaluation_context import build_evaluation_session, validate_evaluation_session
from eval_context.pipeline_validator import validate_repository_intelligence_completeness

def main():
    db = SessionLocal()
    try:
        # Let's find the snapshot from before (61d2b2e6-326a-43ce-9dc0-821d96de339e or ebd19178d761)
        snapshot = db.query(RepositorySnapshot).filter(
            RepositorySnapshot.snapshot_id == "61d2b2e6-326a-43ce-9dc0-821d96de339e"
        ).first()
        
        if not snapshot:
            snapshot = db.query(RepositorySnapshot).filter(
                RepositorySnapshot.folder_structure != None
            ).first()
            
        if not snapshot:
            print("ERROR: No repository snapshot with folder structure found in database!")
            return
            
        print(f"Using RepositorySnapshot: snapshot_id={snapshot.snapshot_id}, commit={snapshot.commit_sha}")
        
        # Create a mock/dummy Evaluation object
        eval_obj = db.query(Evaluation).first()
        if not eval_obj:
            # Create a dummy
            import uuid
            eval_obj = Evaluation(
                evaluation_id=str(uuid.uuid4()),
                project_id="test-project",
                repository_snapshot_id=snapshot.snapshot_id,
                evaluation_status="Running"
            )
            db.add(eval_obj)
            db.commit()
            
        # Run intelligence service
        print("\n--- Running Repository Intelligence ---")
        analysis_data = run_repository_intelligence(db, eval_obj, snapshot.snapshot_id)
        
        print("\n--- Build Evaluation Session ---")
        ctx = {
            "project_name": "Test Project",
            "project_type": "Web Application",
            "github": {
                "repository_statistics": {
                    "total_files": 100,
                    "code_files": 50
                }
            }
        }
        session = build_evaluation_session(
            db=db,
            project_id=eval_obj.project_id,
            evaluation_id=eval_obj.evaluation_id,
            snapshot_id=snapshot.snapshot_id,
            ctx=ctx
        )
        
        print("\n--- Validate Session Stage 4 ---")
        validate_repository_intelligence_completeness(session)
        
        print("\n=== LIFECYCLE AUDIT PASSED successfully ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
