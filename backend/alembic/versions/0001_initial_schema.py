"""initial relational schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-04-11 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_stage", sa.String(length=64), nullable=False, server_default="created"),
        sa.Column("async_task_id", sa.String(length=255), nullable=True),
        sa.Column("async_queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_stage", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("inventory_summary", sa.JSON(), nullable=True),
        sa.Column("retrieval_traces", sa.JSON(), nullable=False),
        sa.Column("usage_statuses", sa.JSON(), nullable=False),
        sa.Column("validation_report", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.create_index("ix_documents_job_id", "documents", ["job_id"])

    op.create_table(
        "evidences",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("subtask", sa.Text(), nullable=False),
        sa.Column("capability_hint", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("workflow_steps", sa.JSON(), nullable=False),
        sa.Column("decision_rules", sa.JSON(), nullable=False),
        sa.Column("topic_modules", sa.JSON(), nullable=False),
        sa.Column("quantitative_signals", sa.JSON(), nullable=False),
        sa.Column("terminology", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("exceptions", sa.JSON(), nullable=False),
        sa.Column("source_document_id", sa.String(length=64), nullable=False, server_default=""),
    )
    op.create_index("ix_evidences_job_id", "evidences", ["job_id"])

    op.create_table(
        "capabilities",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("core_tasks", sa.JSON(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("suggested_packaging", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_capabilities_job_id", "capabilities", ["job_id"])

    op.create_table(
        "skill_plans",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_name", sa.String(length=128), nullable=False),
        sa.Column("description_draft", sa.Text(), nullable=False),
        sa.Column("skill_md_topics", sa.JSON(), nullable=False),
        sa.Column("trigger_conditions", sa.JSON(), nullable=False),
        sa.Column("workflow_outline", sa.JSON(), nullable=False),
        sa.Column("decision_logic", sa.JSON(), nullable=False),
        sa.Column("boundaries", sa.JSON(), nullable=False),
        sa.Column("key_terms", sa.JSON(), nullable=False),
        sa.Column("quantitative_signals", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("exceptions", sa.JSON(), nullable=False),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("scripts", sa.JSON(), nullable=False),
        sa.Column("assets", sa.JSON(), nullable=False),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
    )
    op.create_index("ix_skill_plans_job_id", "skill_plans", ["job_id"])

    op.create_table(
        "generated_skills",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("files", sa.JSON(), nullable=False),
    )
    op.create_index("ix_generated_skills_job_id", "generated_skills", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_skills_job_id", table_name="generated_skills")
    op.drop_table("generated_skills")
    op.drop_index("ix_skill_plans_job_id", table_name="skill_plans")
    op.drop_table("skill_plans")
    op.drop_index("ix_capabilities_job_id", table_name="capabilities")
    op.drop_table("capabilities")
    op.drop_index("ix_evidences_job_id", table_name="evidences")
    op.drop_table("evidences")
    op.drop_index("ix_documents_job_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("jobs")
