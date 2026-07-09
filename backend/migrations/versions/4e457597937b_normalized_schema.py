"""normalized_schema

Revision ID: 4e457597937b
Revises: 
Create Date: 2026-07-02 19:45:05.448346

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e457597937b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with normalized tables and backwards-compatible migration."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Create workspaces table
    if 'workspaces' not in tables:
        op.create_table(
            'workspaces',
            sa.Column('workspace_id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('workspace_id')
        )

    # 2. Handle projects table
    if 'projects' not in tables:
        op.create_table(
            'projects',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('workspace_id', sa.String(length=36), nullable=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('project_type', sa.String(length=50), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('github_url', sa.String(length=512), nullable=True),
            sa.Column('demo_video_url', sa.String(length=512), nullable=True),
            sa.Column('pdf_path', sa.String(length=512), nullable=True),
            sa.Column('ppt_path', sa.String(length=512), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        # Add workspace_id column to projects if missing
        cols = [c['name'] for c in inspector.get_columns('projects')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('projects', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=36), nullable=True))
                batch_op.create_foreign_key('fk_projects_workspaces', 'workspaces', ['workspace_id'], ['workspace_id'])

    # 3. Create repositories table
    if 'repositories' not in tables:
        op.create_table(
            'repositories',
            sa.Column('repository_id', sa.String(length=36), nullable=False),
            sa.Column('project_id', sa.String(length=36), nullable=False),
            sa.Column('github_repository_id', sa.String(length=100), nullable=True),
            sa.Column('github_url', sa.String(length=512), nullable=False),
            sa.Column('owner', sa.String(length=255), nullable=True),
            sa.Column('repository_name', sa.String(length=255), nullable=True),
            sa.Column('default_branch', sa.String(length=100), nullable=True),
            sa.Column('visibility', sa.String(length=50), nullable=True),
            sa.Column('stars', sa.Integer(), nullable=True),
            sa.Column('forks', sa.Integer(), nullable=True),
            sa.Column('open_issues', sa.Integer(), nullable=True),
            sa.Column('license', sa.String(length=100), nullable=True),
            sa.Column('topics', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.PrimaryKeyConstraint('repository_id')
        )
        with op.batch_alter_table('repositories', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_repositories_project_id'), ['project_id'], unique=False)

    # 4. Create repository_snapshots table
    if 'repository_snapshots' not in tables:
        op.create_table(
            'repository_snapshots',
            sa.Column('snapshot_id', sa.String(length=36), nullable=False),
            sa.Column('repository_id', sa.String(length=36), nullable=False),
            sa.Column('commit_sha', sa.String(length=40), nullable=False),
            sa.Column('tree_sha', sa.String(length=40), nullable=True),
            sa.Column('branch', sa.String(length=100), nullable=True),
            sa.Column('readme_snapshot', sa.Text(), nullable=True),
            sa.Column('repository_statistics', sa.Text(), nullable=True),
            sa.Column('folder_structure', sa.Text(), nullable=True),
            sa.Column('technology_summary', sa.Text(), nullable=True),
            sa.Column('dependency_summary', sa.Text(), nullable=True),
            sa.Column('architecture_summary', sa.Text(), nullable=True),
            sa.Column('last_commit_timestamp', sa.DateTime(), nullable=True),
            sa.Column('snapshot_timestamp', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['repository_id'], ['repositories.repository_id'], ),
            sa.PrimaryKeyConstraint('snapshot_id')
        )
        with op.batch_alter_table('repository_snapshots', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_repository_snapshots_commit_sha'), ['commit_sha'], unique=False)
            batch_op.create_index(batch_op.f('ix_repository_snapshots_repository_id'), ['repository_id'], unique=False)

    # 5. Create technologies and dependencies tables
    if 'technologies' not in tables:
        op.create_table(
            'technologies',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('repository_id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('version', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['repository_id'], ['repositories.repository_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('technologies', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_technologies_name'), ['name'], unique=False)
            batch_op.create_index(batch_op.f('ix_technologies_repository_id'), ['repository_id'], unique=False)

    if 'dependencies' not in tables:
        op.create_table(
            'dependencies',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('repository_id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('version', sa.String(length=50), nullable=True),
            sa.Column('type', sa.String(length=50), nullable=False),
            sa.ForeignKeyConstraint(['repository_id'], ['repositories.repository_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('dependencies', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_dependencies_name'), ['name'], unique=False)
            batch_op.create_index(batch_op.f('ix_dependencies_repository_id'), ['repository_id'], unique=False)

    # 6. Create evaluations table
    if 'evaluations' not in tables:
        op.create_table(
            'evaluations',
            sa.Column('evaluation_id', sa.String(length=36), nullable=False),
            sa.Column('project_id', sa.String(length=36), nullable=False),
            sa.Column('repository_snapshot_id', sa.String(length=36), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.Column('evaluation_duration', sa.Float(), nullable=True),
            sa.Column('overall_score', sa.Float(), nullable=True),
            sa.Column('verdict', sa.String(length=20), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('evaluation_status', sa.String(length=20), nullable=True),
            sa.Column('llm_model', sa.String(length=100), nullable=True),
            sa.Column('embedding_model', sa.String(length=100), nullable=True),
            sa.Column('evaluation_version', sa.String(length=50), nullable=True),
            sa.Column('prompt_version', sa.String(length=50), nullable=True),
            sa.Column('rubric_version', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.ForeignKeyConstraint(['repository_snapshot_id'], ['repository_snapshots.snapshot_id'], ),
            sa.PrimaryKeyConstraint('evaluation_id')
        )
        with op.batch_alter_table('evaluations', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_evaluations_project_id'), ['project_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_evaluations_repository_snapshot_id'), ['repository_snapshot_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_evaluations_timestamp'), ['timestamp'], unique=False)
    else:
        # Detect if old evaluations table matches old columns (missing evaluation_id)
        eval_cols = [c['name'] for c in inspector.get_columns('evaluations')]
        if 'evaluation_id' not in eval_cols:
            # Rename old evaluations to agent_evaluations
            op.rename_table('evaluations', 'agent_evaluations')
            tables.append('agent_evaluations')
            # Now create the new evaluations table
            op.create_table(
                'evaluations',
                sa.Column('evaluation_id', sa.String(length=36), nullable=False),
                sa.Column('project_id', sa.String(length=36), nullable=False),
                sa.Column('repository_snapshot_id', sa.String(length=36), nullable=True),
                sa.Column('timestamp', sa.DateTime(), nullable=True),
                sa.Column('evaluation_duration', sa.Float(), nullable=True),
                sa.Column('overall_score', sa.Float(), nullable=True),
                sa.Column('verdict', sa.String(length=20), nullable=True),
                sa.Column('confidence', sa.Float(), nullable=True),
                sa.Column('evaluation_status', sa.String(length=20), nullable=True),
                sa.Column('llm_model', sa.String(length=100), nullable=True),
                sa.Column('embedding_model', sa.String(length=100), nullable=True),
                sa.Column('evaluation_version', sa.String(length=50), nullable=True),
                sa.Column('prompt_version', sa.String(length=50), nullable=True),
                sa.Column('rubric_version', sa.String(length=50), nullable=True),
                sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
                sa.ForeignKeyConstraint(['repository_snapshot_id'], ['repository_snapshots.snapshot_id'], ),
                sa.PrimaryKeyConstraint('evaluation_id')
            )
            with op.batch_alter_table('evaluations', schema=None) as batch_op:
                batch_op.create_index(batch_op.f('ix_evaluations_project_id'), ['project_id'], unique=False)
                batch_op.create_index(batch_op.f('ix_evaluations_repository_snapshot_id'), ['repository_snapshot_id'], unique=False)
                batch_op.create_index(batch_op.f('ix_evaluations_timestamp'), ['timestamp'], unique=False)

    # 7. Create repository_files and repository_folders
    if 'repository_files' not in tables:
        op.create_table(
            'repository_files',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('snapshot_id', sa.String(length=36), nullable=False),
            sa.Column('path', sa.String(length=512), nullable=False),
            sa.Column('size_bytes', sa.Integer(), nullable=True),
            sa.Column('language', sa.String(length=100), nullable=True),
            sa.ForeignKeyConstraint(['snapshot_id'], ['repository_snapshots.snapshot_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('repository_files', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_repository_files_snapshot_id'), ['snapshot_id'], unique=False)

    if 'repository_folders' not in tables:
        op.create_table(
            'repository_folders',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('snapshot_id', sa.String(length=36), nullable=False),
            sa.Column('path', sa.String(length=512), nullable=False),
            sa.ForeignKeyConstraint(['snapshot_id'], ['repository_snapshots.snapshot_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('repository_folders', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_repository_folders_snapshot_id'), ['snapshot_id'], unique=False)

    # 8. Create agent_evaluations table or migrate old evaluations (already renamed)
    if 'agent_evaluations' not in tables:
        op.create_table(
            'agent_evaluations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('evaluation_id', sa.String(length=36), nullable=False),
            sa.Column('agent_name', sa.String(length=100), nullable=False),
            sa.Column('score', sa.Float(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('execution_time', sa.Float(), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.evaluation_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('agent_evaluations', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_agent_evaluations_agent_name'), ['agent_name'], unique=False)
            batch_op.create_index(batch_op.f('ix_agent_evaluations_evaluation_id'), ['evaluation_id'], unique=False)
    else:
        # Migrate renamed agent_evaluations columns
        agent_cols = [c['name'] for c in inspector.get_columns('agent_evaluations')]
        with op.batch_alter_table('agent_evaluations', schema=None) as batch_op:
            if 'evaluation_id' not in agent_cols:
                batch_op.add_column(sa.Column('evaluation_id', sa.String(length=36), nullable=True))
                batch_op.create_foreign_key('fk_agent_evaluations_evaluations', 'evaluations', ['evaluation_id'], ['evaluation_id'])
            if 'confidence' not in agent_cols:
                batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))
            if 'execution_time' not in agent_cols:
                batch_op.add_column(sa.Column('execution_time', sa.Float(), nullable=True))
            if 'status' not in agent_cols:
                batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True, server_default='completed'))
            if 'findings' in agent_cols and 'summary' not in agent_cols:
                batch_op.alter_column('findings', new_column_name='summary', existing_type=sa.Text())
            # Index recreation
            batch_op.create_index(batch_op.f('ix_agent_evaluations_agent_name'), ['agent_name'], unique=False)
            batch_op.create_index(batch_op.f('ix_agent_evaluations_evaluation_id'), ['evaluation_id'], unique=False)

    # 9. Create evaluation_events, evidence, and recommendations
    if 'evaluation_events' not in tables:
        op.create_table(
            'evaluation_events',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('evaluation_id', sa.String(length=36), nullable=False),
            sa.Column('event_name', sa.String(length=100), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.Column('duration', sa.Float(), nullable=True),
            sa.Column('event_metadata', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.evaluation_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('evaluation_events', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_evaluation_events_evaluation_id'), ['evaluation_id'], unique=False)

    if 'evidence' not in tables:
        op.create_table(
            'evidence',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('evaluation_id', sa.String(length=36), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('finding', sa.Text(), nullable=False),
            sa.Column('file_path', sa.String(length=512), nullable=True),
            sa.Column('line_start', sa.Integer(), nullable=True),
            sa.Column('line_end', sa.Integer(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('severity', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.evaluation_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('evidence', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_evidence_evaluation_id'), ['evaluation_id'], unique=False)

    # 10. Handle reports table
    if 'reports' not in tables:
        op.create_table(
            'reports',
            sa.Column('report_id', sa.String(length=36), nullable=False),
            sa.Column('evaluation_id', sa.String(length=36), nullable=False),
            sa.Column('report_type', sa.String(length=50), nullable=True),
            sa.Column('file_path', sa.String(length=512), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=True),
            sa.Column('checksum', sa.String(length=64), nullable=True),
            sa.Column('generated_at', sa.DateTime(), nullable=True),
            sa.Column('generation_time', sa.Float(), nullable=True),
            sa.Column('version', sa.String(length=20), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.evaluation_id'], ),
            sa.PrimaryKeyConstraint('report_id')
        )
        with op.batch_alter_table('reports', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_reports_evaluation_id'), ['evaluation_id'], unique=False)
    else:
        # Migrate reports columns
        report_cols = [c['name'] for c in inspector.get_columns('reports')]
        with op.batch_alter_table('reports', schema=None) as batch_op:
            if 'id' in report_cols:
                batch_op.alter_column('id', new_column_name='report_id', existing_type=sa.String(length=36))
            if 'pdf_path' in report_cols:
                batch_op.alter_column('pdf_path', new_column_name='file_path', existing_type=sa.String(length=512))
            if 'evaluation_id' not in report_cols:
                batch_op.add_column(sa.Column('evaluation_id', sa.String(length=36), nullable=True))
                batch_op.create_foreign_key('fk_reports_evaluations', 'evaluations', ['evaluation_id'], ['evaluation_id'])
            if 'report_type' not in report_cols:
                batch_op.add_column(sa.Column('report_type', sa.String(length=50), nullable=True, server_default='PDF'))
            if 'file_size' not in report_cols:
                batch_op.add_column(sa.Column('file_size', sa.Integer(), nullable=True))
            if 'checksum' not in report_cols:
                batch_op.add_column(sa.Column('checksum', sa.String(length=64), nullable=True))
            if 'generation_time' not in report_cols:
                batch_op.add_column(sa.Column('generation_time', sa.Float(), nullable=True))
            if 'version' not in report_cols:
                batch_op.add_column(sa.Column('version', sa.String(length=20), nullable=True, server_default='1.0.0'))
            # Recreate indices
            batch_op.create_index(batch_op.f('ix_reports_evaluation_id'), ['evaluation_id'], unique=False)

    if 'recommendations' not in tables:
        op.create_table(
            'recommendations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('evaluation_id', sa.String(length=36), nullable=False),
            sa.Column('evidence_id', sa.String(length=36), nullable=True),
            sa.Column('priority', sa.String(length=20), nullable=True),
            sa.Column('category', sa.String(length=100), nullable=True),
            sa.Column('recommendation', sa.Text(), nullable=False),
            sa.Column('expected_score_gain', sa.Float(), nullable=True),
            sa.Column('estimated_effort', sa.String(length=50), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.evaluation_id'], ),
            sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('recommendations', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_recommendations_evaluation_id'), ['evaluation_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_recommendations_evidence_id'), ['evidence_id'], unique=False)

    # 11. Run data backfill for existing evaluations & reports
    connection = op.get_bind()
    projects_result = connection.execute(sa.text("SELECT id, name, github_url, created_at, status FROM projects")).fetchall()
    
    for project_id, name, github_url, created_at, status in projects_result:
        repo_id = str(uuid.uuid4())
        snapshot_id = str(uuid.uuid4())
        evaluation_id = str(uuid.uuid4())

        # If repo url is available, create repository + snapshot
        if github_url:
            connection.execute(sa.text(
                "INSERT INTO repositories (repository_id, project_id, github_url, visibility, created_at, updated_at) "
                "VALUES (:repo_id, :project_id, :github_url, 'public', :created_at, :created_at)"
            ), {"repo_id": repo_id, "project_id": project_id, "github_url": github_url, "created_at": created_at})

            connection.execute(sa.text(
                "INSERT INTO repository_snapshots (snapshot_id, repository_id, commit_sha, branch, snapshot_timestamp) "
                "VALUES (:snapshot_id, :repo_id, 'migrated-commit', 'main', :created_at)"
            ), {"snapshot_id": snapshot_id, "repo_id": repo_id, "created_at": created_at})
        else:
            snapshot_id = None

        # Fetch report details if status is done
        overall_score = None
        verdict = None
        if status == 'done':
            report_row = connection.execute(sa.text(
                "SELECT report_id, overall_score, verdict FROM reports WHERE project_id = :project_id"
            ), {"project_id": project_id}).fetchone()
            
            if report_row:
                old_report_id, overall_score, verdict = report_row

                # Create main evaluation record matching report
                connection.execute(sa.text(
                    "INSERT INTO evaluations (evaluation_id, project_id, repository_snapshot_id, timestamp, overall_score, verdict, evaluation_status) "
                    "VALUES (:evaluation_id, :project_id, :snapshot_id, :timestamp, :overall_score, :verdict, 'Completed')"
                ), {
                    "evaluation_id": evaluation_id,
                    "project_id": project_id,
                    "snapshot_id": snapshot_id,
                    "timestamp": created_at,
                    "overall_score": overall_score,
                    "verdict": verdict
                })

                # Update old evaluations (now renamed to agent_evaluations) to reference new evaluation
                connection.execute(sa.text(
                    "UPDATE agent_evaluations SET evaluation_id = :evaluation_id WHERE project_id = :project_id"
                ), {"evaluation_id": evaluation_id, "project_id": project_id})

                # Update reports table to reference the new evaluation_id
                connection.execute(sa.text(
                    "UPDATE reports SET evaluation_id = :evaluation_id WHERE project_id = :project_id"
                ), {"evaluation_id": evaluation_id, "project_id": project_id})


def downgrade() -> None:
    """Downgrade schema."""
    # SQLite batch alteration downgrades can be complex.
    # For backward-compatible deployments, rollback downgrades drop the new tables and indexes.
    op.drop_table('recommendations')
    op.drop_table('evidence')
    op.drop_table('evaluation_events')
    op.drop_table('agent_evaluations')
    op.drop_table('repository_folders')
    op.drop_table('repository_files')
    op.drop_table('evaluations')
    op.drop_table('dependencies')
    op.drop_table('technologies')
    op.drop_table('repository_snapshots')
    op.drop_table('repositories')
    op.drop_table('workspaces')
