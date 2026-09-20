import importlib
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.app.models.chunk_embedding import ChunkEmbedding
from backend.app.core.config import settings


def test_alembic_config_and_script_discovery():
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "001_initial_schema"


def test_pgvector_model_vector_dimension():
    assert settings.EMBEDDING_DIMENSION == 384
    col = ChunkEmbedding.__table__.columns["embedding"]
    # Verify column type is Vector with dimension 384
    assert hasattr(col.type, "dim")
    assert col.type.dim == 384
