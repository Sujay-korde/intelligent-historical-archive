"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("record_type", sa.String(length=64), nullable=False, server_default="document"),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="INGESTED"),
        sa.Column("processing_stage", sa.String(length=64), nullable=False, server_default="INITIAL"),
        sa.Column("quality_score", sa.Numeric(5, 2), server_default="0.0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source", "source_id", name="uq_documents_source_source_id"),
    )
    op.create_index("ix_documents_source", "documents", ["source"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_processing_stage", "documents", ["processing_stage"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    # Document Media Assets table
    op.create_table(
        "document_media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_role", sa.String(length=32), nullable=False, server_default="primary"),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_media_assets_document_id", "document_media_assets", ["document_id"])
    op.create_index("ix_document_media_assets_checksum_sha256", "document_media_assets", ["checksum_sha256"])

    # Document Metadata table
    op.create_table(
        "document_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("creators", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("date_raw", sa.String(length=128), nullable=True),
        sa.Column("date_start", sa.Date(), nullable=True),
        sa.Column("date_end", sa.Date(), nullable=True),
        sa.Column("date_is_circa", sa.Boolean(), server_default="false"),
        sa.Column("locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("language", sa.String(length=64), server_default="English"),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("subjects", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("rights", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("external_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ai_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_metadata_document_id", "document_metadata", ["document_id"])
    op.create_index("ix_document_metadata_date_start", "document_metadata", ["date_start"])
    op.create_index("ix_document_metadata_date_end", "document_metadata", ["date_end"])

    # Document Chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # Chunk Embeddings table (pgvector)
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="384"),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("chunk_id", "model_name", "model_version", name="uq_chunk_embedding_model"),
    )
    op.create_index("ix_chunk_embeddings_chunk_id", "chunk_embeddings", ["chunk_id"])
    op.create_index("ix_chunk_embeddings_is_active", "chunk_embeddings", ["is_active"])

    # Entities table
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("authority_uri", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_type", "normalized_name", name="uq_entities_type_name"),
    )
    op.create_index("ix_entities_normalized_name", "entities", ["normalized_name"])
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])

    # Document Entities table
    op.create_table(
        "document_entities",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="1.0"),
        sa.Column("provenance", sa.String(length=32), nullable=False, server_default="SOURCE"),
        sa.Column("relationship_type", sa.String(length=64), nullable=False, server_default="MENTIONS"),
        sa.PrimaryKeyConstraint("document_id", "entity_id", "relationship_type"),
    )
    op.create_index("ix_document_entities_entity_id", "document_entities", ["entity_id"])

    # Relationships table
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="1.0"),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_relationships_source_entity_id", "relationships", ["source_entity_id"])
    op.create_index("ix_relationships_target_entity_id", "relationships", ["target_entity_id"])
    op.create_index("ix_relationships_relationship_type", "relationships", ["relationship_type"])
    op.create_index("ix_relationships_source_document_id", "relationships", ["source_document_id"])

    # Processing Jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("current_step", sa.String(length=128), nullable=False, server_default="QUEUED"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_stack", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
    op.create_index("ix_processing_jobs_created_at", "processing_jobs", ["created_at"])

    # Search History table
    op.create_table(
        "search_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("search_type", sa.String(length=32), nullable=False, server_default="HYBRID"),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_time_ms", sa.Numeric(8, 2), nullable=True),
        sa.Column("selected_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_search_history_created_at", "search_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("search_history")
    op.drop_table("processing_jobs")
    op.drop_table("relationships")
    op.drop_table("document_entities")
    op.drop_table("entities")
    op.drop_table("chunk_embeddings")
    op.drop_table("document_chunks")
    op.drop_table("document_metadata")
    op.drop_table("document_media_assets")
    op.drop_table("documents")
    op.execute("DROP EXTENSION IF EXISTS vector;")
