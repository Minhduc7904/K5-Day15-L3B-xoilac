import hashlib
import secrets


class TokenService:
    """Sinh token phiên dạng opaque và băm SHA-256 để lưu. CSDL chỉ giữ hash."""

    def generate(self) -> str:
        return secrets.token_urlsafe(32)

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
