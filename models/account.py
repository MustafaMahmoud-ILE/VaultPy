from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Account:
    """Represents a single account/secret entry in the vault."""
    id: Optional[int]
    service: str
    username: str
    password_encrypted: bytes
    totp_secret_encrypted: Optional[bytes] = None
    notes_encrypted: Optional[bytes] = None
    created_at: Optional[str] = None

    def __repr__(self):
        return f"<Account(service='{self.service}', username='{self.username}')>"
