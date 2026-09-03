"""Production-Safe Logging & Secret Redaction (Phase 18C).

Ensures that no passwords, JWT tokens, Bearer authorization headers, API keys,
X-Agent-Key headers, Razorpay credentials/signatures, or DATABASE_URL strings
appear in application logs or exception diagnostics.
"""

import logging
import re
from typing import Any, Dict, List

# Compiled regex patterns for redaction
REDACTION_PATTERNS = [
    # 1. Bearer / Authorization tokens
    (re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]+\b"), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(?i)\bBasic\s+[a-zA-Z0-9+/=]+\b"), "Basic [REDACTED_CREDENTIALS]"),

    # 2. JWT Tokens (header.payload.signature format or eyJ... prefix)
    (re.compile(r"\beyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,}\b"), "[REDACTED_JWT]"),
    (re.compile(r"\beyJ[a-zA-Z0-9_-]{25,}\b"), "[REDACTED_JWT]"),

    # 3. Agent-to-Agent keys
    (re.compile(r"\bag_live_[a-zA-Z0-9_-]{10,}\b"), "[REDACTED_AGENT_KEY]"),

    # 4. Razorpay credentials & webhook signatures
    (re.compile(r"\brzp_live_[a-zA-Z0-9_-]{10,}\b"), "[REDACTED_RAZORPAY_KEY]"),
    (re.compile(r"\brzp_test_[a-zA-Z0-9_-]{10,}\b"), "[REDACTED_RAZORPAY_KEY]"),

    # 5. Generic API keys (Groq, OpenAI, etc.)
    (re.compile(r"\bgsk_[a-zA-Z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),

    # 6. Database URLs containing passwords (postgres://user:password@host...)
    (
        re.compile(r"(postgres(?:ql)?://[^:]+:)([^@]+)(@[^\s/]+/[^\s]+)"),
        r"\1[REDACTED]\3",
    ),

    # 7. Private Keys
    (
        re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL),
        "[REDACTED_PRIVATE_KEY]",
    ),

    # 8. Password key-value pairs in JSON / log text
    (
        re.compile(r'(?i)(["\']?(?:password|passwd|pwd|secret|token|api_key)["\']?\s*[:=]\s*["\'])([^"\']{1,128})(["\'])'),
        r"\1[REDACTED]\3",
    ),
]


def redact_sensitive_text(text: str) -> str:
    """Recursively replaces sensitive patterns with safe redaction placeholders."""
    if not text or not isinstance(text, str):
        return text

    sanitized = text
    for pattern, replacement in REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SensitiveDataRedactionFilter(logging.Filter):
    """Logging filter that redacts credentials, keys, and tokens from all log output."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)

        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive_text(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: redact_sensitive_text(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }

        if record.exc_text and isinstance(record.exc_text, str):
            record.exc_text = redact_sensitive_text(record.exc_text)

        return True


def setup_security_logging() -> None:
    """Installs the SensitiveDataRedactionFilter on root and common loggers."""
    loggers_to_protect = [
        logging.getLogger(),
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("fastapi"),
        logging.getLogger("app"),
    ]

    for log in loggers_to_protect:
        # Avoid duplicate filters
        if not any(isinstance(f, SensitiveDataRedactionFilter) for f in log.filters):
            log.addFilter(SensitiveDataRedactionFilter())
