from __future__ import annotations

import hashlib
import os
import re
import secrets
import smtplib
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class ApiKeyIssueResult:
    email: str
    prefix: str
    api_key: str
    delivery_method: str
    delivery_detail: str

    def public_dict(self, *, include_key: bool = False) -> dict:
        payload = {
            "ok": True,
            "email": self.email,
            "key_prefix": self.prefix,
            "delivery_method": self.delivery_method,
            "delivery_detail": self.delivery_detail,
        }
        if include_key:
            payload["api_key"] = self.api_key
        return payload


def issue_api_key(
    email: str,
    *,
    name: str = "",
    organization: str = "",
    intended_use: str = "",
    terms_version: str = "",
    db_path: Optional[Path] = None,
) -> ApiKeyIssueResult:
    """Create a free API key, store only its hash, and deliver the secret."""

    normalized_email = normalize_email(email)
    api_key = _generate_api_key()
    prefix = api_key[:16]
    now = _now()
    path = db_path or api_key_db_path()
    _init_db(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        request_limit = int(os.environ.get("QQ_API_KEY_REQUESTS_PER_DAY", "3"))
        if request_limit > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
            recent = connection.execute(
                "SELECT COUNT(*) FROM api_key_requests WHERE email = ? AND created_at >= ?",
                (normalized_email, cutoff),
            ).fetchone()[0]
            if recent >= request_limit:
                raise ValueError(
                    "API key request limit reached for this email address; try again later"
                )

        connection.execute(
            """
            INSERT INTO api_keys (
              email, key_hash, key_prefix, name, organization, intended_use, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_email,
                hash_api_key(api_key),
                prefix,
                name,
                organization,
                intended_use,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO api_key_requests (
              email, key_prefix, name, organization, intended_use, created_at,
              terms_version, terms_accepted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_email,
                prefix,
                name,
                organization,
                intended_use,
                now,
                terms_version,
                now if terms_version else "",
            ),
        )
        # Delivery is part of the transaction. If SMTP fails, the unusable key and
        # request record are rolled back instead of becoming orphaned rows.
        method, detail = deliver_api_key(
            normalized_email,
            api_key,
            name=name,
            organization=organization,
        )
    return ApiKeyIssueResult(
        email=normalized_email,
        prefix=prefix,
        api_key=api_key,
        delivery_method=method,
        delivery_detail=detail,
    )


def validate_api_key(api_key: str, *, db_path: Optional[Path] = None) -> bool:
    """Return True when the supplied key exists and has not been revoked."""

    if not api_key:
        return False
    path = db_path or api_key_db_path()
    if not path.exists():
        return False
    prefix = api_key[:16]
    digest = hash_api_key(api_key)
    with closing(sqlite3.connect(path)) as connection, connection:
        row = connection.execute(
            """
            SELECT id
            FROM api_keys
            WHERE key_prefix = ?
              AND key_hash = ?
              AND revoked_at IS NULL
            """,
            (prefix, digest),
        ).fetchone()
        if not row:
            return False
        connection.execute(
            "UPDATE api_keys SET last_used_at = ?, usage_count = usage_count + 1 WHERE id = ?",
            (_now(), row[0]),
        )
    return True


def revoke_api_key(api_key: str, *, db_path: Optional[Path] = None) -> bool:
    """Revoke a key and return whether an active matching key was found."""

    if not api_key:
        return False
    path = db_path or api_key_db_path()
    if not path.exists():
        return False
    with closing(sqlite3.connect(path)) as connection, connection:
        cursor = connection.execute(
            """
            UPDATE api_keys
            SET revoked_at = ?
            WHERE key_prefix = ? AND key_hash = ? AND revoked_at IS NULL
            """,
            (_now(), api_key[:16], hash_api_key(api_key)),
        )
        return cursor.rowcount > 0


def normalize_email(email: str) -> str:
    normalized = str(email).strip().lower()
    if not EMAIL_RE.match(normalized):
        raise ValueError("a valid email address is required")
    return normalized


def hash_api_key(api_key: str) -> str:
    pepper = os.environ.get("QQ_API_KEY_PEPPER", "")
    return hashlib.sha256(f"{pepper}:{api_key}".encode("utf-8")).hexdigest()


def api_key_db_path() -> Path:
    configured = os.environ.get("QQ_API_KEY_DB", "")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".quantity_quality" / "api_keys.sqlite3"


def api_keys_required() -> bool:
    return _truthy(os.environ.get("QQ_API_REQUIRE_KEY", "0"))


def return_keys_in_response() -> bool:
    return _truthy(os.environ.get("QQ_API_KEY_RETURN_IN_RESPONSE", "0"))


def deliver_api_key(
    email: str,
    api_key: str,
    *,
    name: str = "",
    organization: str = "",
) -> tuple[str, str]:
    """Deliver a key by SMTP or development console output."""

    mode = os.environ.get("QQ_API_EMAIL_MODE", "console").strip().lower()
    if mode == "disabled":
        return "disabled", "API key generated; email delivery is disabled."
    if mode == "smtp":
        _send_smtp_email(email, api_key, name=name, organization=organization)
        return "smtp", "API key emailed."

    print(
        _email_body(email=email, api_key=api_key, name=name, organization=organization),
        file=sys.stderr,
    )
    return "console", "Development mode: API key printed to server stderr."


def _send_smtp_email(
    email: str,
    api_key: str,
    *,
    name: str = "",
    organization: str = "",
) -> None:
    host = os.environ.get("QQ_SMTP_HOST", "")
    sender = os.environ.get("QQ_SMTP_FROM", "")
    if not host or not sender:
        raise RuntimeError("QQ_SMTP_HOST and QQ_SMTP_FROM are required when QQ_API_EMAIL_MODE=smtp")

    port = int(os.environ.get("QQ_SMTP_PORT", "587"))
    username = os.environ.get("QQ_SMTP_USERNAME", "")
    password = os.environ.get("QQ_SMTP_PASSWORD", "")
    use_tls = _truthy(os.environ.get("QQ_SMTP_TLS", "1"))

    message = EmailMessage()
    message["Subject"] = "Your Exergy Factor API key"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        _email_body(email=email, api_key=api_key, name=name, organization=organization)
    )

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username or password:
            smtp.login(username, password)
        smtp.send_message(message)


def _email_body(
    *,
    email: str,
    api_key: str,
    name: str = "",
    organization: str = "",
) -> str:
    greeting = f"Hi {name.strip()}," if name.strip() else "Hi,"
    base_url = os.environ.get("QQ_API_PUBLIC_BASE_URL", "https://api.exergyfactor.com/v1").rstrip(
        "/"
    )
    org_line = f"\nOrganization: {organization.strip()}" if organization.strip() else ""
    return f"""{greeting}

Here is your free Exergy Factor API key:

{api_key}

Example:

curl -H "X-API-Key: {api_key}" {base_url}/tiers

Keep this key private. The API exposes the deterministic Quantity + Quality Python library; it does not use an agent or hidden calculations.{org_line}
"""


def _generate_api_key() -> str:
    prefix = os.environ.get("QQ_API_KEY_PREFIX", "qq_live").strip().strip("_") or "qq_live"
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL,
              key_hash TEXT NOT NULL UNIQUE,
              key_prefix TEXT NOT NULL,
              name TEXT NOT NULL DEFAULT '',
              organization TEXT NOT NULL DEFAULT '',
              intended_use TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              last_used_at TEXT,
              revoked_at TEXT,
              usage_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS api_key_requests (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL,
              key_prefix TEXT NOT NULL,
              name TEXT NOT NULL DEFAULT '',
              organization TEXT NOT NULL DEFAULT '',
              intended_use TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              terms_version TEXT NOT NULL DEFAULT '',
              terms_accepted_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        request_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(api_key_requests)")
        }
        if "terms_version" not in request_columns:
            connection.execute(
                "ALTER TABLE api_key_requests ADD COLUMN terms_version TEXT NOT NULL DEFAULT ''"
            )
        if "terms_accepted_at" not in request_columns:
            connection.execute(
                "ALTER TABLE api_key_requests ADD COLUMN terms_accepted_at TEXT NOT NULL DEFAULT ''"
            )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_email ON api_keys(email)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
