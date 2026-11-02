import json
import os

from cryptography.fernet import Fernet, InvalidToken


class SecretVault:
    def __init__(self, settings):
        key = settings.credential_key.get_secret_value()
        if not key:
            if settings.auth_backend != "LocalAccess":
                raise ValueError("DAYLOOM_CREDENTIAL_KEY is required for account mode")
            path = settings.credential_key_file
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if path.stat().st_mode & 0o077:
                    raise ValueError("Credential key file must be private (mode 0600)") from None
                key = path.read_bytes()
            else:
                key = Fernet.generate_key()
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(key)
        self.cipher = Fernet(key)

    def seal(self, value: dict, purpose: str) -> str:
        payload = json.dumps({"purpose": purpose, "value": value}, separators=(",", ":"))
        return self.cipher.encrypt(payload.encode()).decode()

    def open(self, token: str, purpose: str) -> dict:
        payload = json.loads(self.cipher.decrypt(token.encode()))
        if payload["purpose"] != purpose:
            raise InvalidToken("Credential binding mismatch")
        return payload["value"]
