from backend.app.core.config import Settings


def test_default_settings():
    config = Settings()
    assert config.PROJECT_NAME == "Intelligent Knowledge Archive"
    assert config.API_V1_STR == "/api/v1"
    assert config.STORAGE_BACKEND in ["local", "s3"]
    assert config.EMBEDDING_DIMENSION == 384
    assert isinstance(config.CORS_ORIGINS, list)


def test_cors_origins_parsing():
    # Test comma-separated string parsing
    config = Settings(CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert config.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]

    # Test JSON string parsing
    config = Settings(CORS_ORIGINS='["http://localhost:3000", "https://app.example.com"]')
    assert config.CORS_ORIGINS == ["http://localhost:3000", "https://app.example.com"]
