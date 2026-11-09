import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException
from pydantic import SecretStr

import core.security as security
from core.config import settings
from schemas.auth import RegisterRequest


@pytest.fixture(autouse=True)
def restore_rsa_globals():
    old_private_key = security._rsa_private_key
    old_public_key_pem = security._rsa_public_key_pem
    yield
    security._rsa_private_key = old_private_key
    security._rsa_public_key_pem = old_public_key_pem


@pytest.fixture
def rsa_key_file(tmp_path, monkeypatch):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    key_path = tmp_path / "auth_rsa_private_key.pem"
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    monkeypatch.setattr(settings, "rsa_private_key_path", str(key_path))
    monkeypatch.setattr(settings, "rsa_private_key_password", None)
    return private_key, key_path


def test_initialize_rsa_keys_uses_persistent_file(rsa_key_file):
    _, key_path = rsa_key_file

    security.initialize_rsa_keys()
    first_public_key = security.get_public_key_pem()

    security.initialize_rsa_keys()
    second_public_key = security.get_public_key_pem()

    loaded_key = security.load_rsa_private_key(key_path)
    assert loaded_key.key_size == 2048
    assert first_public_key == second_public_key
    assert "BEGIN PUBLIC KEY" in first_public_key


def test_decrypt_password_round_trip(rsa_key_file):
    private_key, _ = rsa_key_file
    security.initialize_rsa_keys()

    ciphertext = private_key.public_key().encrypt(
        b"correct horse battery staple",
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_password = base64.b64encode(ciphertext).decode("utf-8")

    assert (
        security.decrypt_password(encrypted_password)
        == "correct horse battery staple"
    )


def test_decrypt_password_rejects_invalid_ciphertext(rsa_key_file):
    security.initialize_rsa_keys()

    with pytest.raises(ValueError, match="密码密文格式无效"):
        security.decrypt_password("not-valid-base64")


def test_missing_private_key_fails_clearly(tmp_path, monkeypatch):
    missing_path = tmp_path / "missing.pem"
    monkeypatch.setattr(settings, "rsa_private_key_path", str(missing_path))
    monkeypatch.setattr(settings, "rsa_private_key_password", None)

    with pytest.raises(RuntimeError, match="private key file not found"):
        security.initialize_rsa_keys()


def test_encrypted_private_key_supports_password(tmp_path, monkeypatch):
    password = "test-key-password"
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    key_path = tmp_path / "encrypted.pem"
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                password.encode("utf-8")
            ),
        )
    )

    monkeypatch.setattr(settings, "rsa_private_key_path", str(key_path))
    monkeypatch.setattr(
        settings,
        "rsa_private_key_password",
        SecretStr(password),
    )

    security.initialize_rsa_keys()
    public_key = security.get_public_key_pem()

    assert "BEGIN PUBLIC KEY" in public_key


@pytest.mark.asyncio
async def test_register_invalid_ciphertext_returns_bad_request(rsa_key_file):
    security.initialize_rsa_keys()
    request = RegisterRequest(
        email="user@example.com",
        password="not-valid-base64",
        confirm_password="not-valid-base64",
    )

    with pytest.raises(HTTPException) as exc_info:
        from api.auth import register

        await register(request, db=None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "密码密文格式无效"
