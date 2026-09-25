import pytest
from app.config import DEFAULT_DEV_SECRET, Settings


def test_dev_environment_allows_default_secret():
    """Local development environment allows default fallback secret without error."""
    s = Settings(
        ENV="development",
        JWT_SECRET=DEFAULT_DEV_SECRET,
        SECRET_KEY=DEFAULT_DEV_SECRET,
    )
    assert s.JWT_SECRET == DEFAULT_DEV_SECRET
    assert s.SECRET_KEY == DEFAULT_DEV_SECRET


def test_production_rejects_default_secret():
    """Production environment strictly refuses to start with the public default secret."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENV="production",
            JWT_SECRET=DEFAULT_DEV_SECRET,
            SECRET_KEY=DEFAULT_DEV_SECRET,
        )
    assert "Refusing to start with an insecure default secret" in str(exc_info.value)
    assert "JWT_SECRET must be set to a unique value >= 32 characters" in str(exc_info.value)


def test_production_rejects_short_secret():
    """Production environment rejects secrets shorter than 32 characters."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENV="production",
            JWT_SECRET="short_secret_under_32_chars",
            SECRET_KEY="short_secret_under_32_chars",
        )
    assert "Refusing to start with an insecure default secret" in str(exc_info.value)


def test_production_rejects_empty_secret():
    """Production environment rejects empty or whitespace-only secrets."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENV="production",
            JWT_SECRET="   ",
            SECRET_KEY="   ",
        )
    assert "Refusing to start with an insecure default secret" in str(exc_info.value)


def test_production_accepts_secure_secret():
    """Production environment boots normally when a unique 32+ character secret is provided."""
    secure_secret = "production-secure-entropy-key-over-32-characters-long!!"
    s = Settings(
        ENV="production",
        JWT_SECRET=secure_secret,
    )
    assert s.JWT_SECRET == secure_secret
    # SECRET_KEY should automatically synchronize if left default
    assert s.SECRET_KEY == secure_secret
