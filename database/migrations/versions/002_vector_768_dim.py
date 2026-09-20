"""002_vector_768_dim

Revision ID: 002_vector_768_dim
Revises: 001_initial_schema
Create Date: 2026-09-20 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "002_vector_768_dim"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update chunk_embeddings.embedding vector dimension from 384 to 768
    op.alter_column(
        "chunk_embeddings",
        "embedding",
        type_=Vector(768),
        existing_type=Vector(384),
        existing_nullable=False,
    )
    op.alter_column(
        "chunk_embeddings",
        "dimension",
        server_default="768",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "chunk_embeddings",
        "embedding",
        type_=Vector(384),
        existing_type=Vector(768),
        existing_nullable=False,
    )
    op.alter_column(
        "chunk_embeddings",
        "dimension",
        server_default="384",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
