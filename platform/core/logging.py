import logging
import re


def redact(message: str) -> str:
    message = re.sub(r"(/access/)[^/\s]+", r"\1[redacted]", message)
    message = re.sub(r"(/volunteer-access/)[^/\s]+", r"\1[redacted]", message)
    message = re.sub(r"invitation=[^&\s]+", "invitation=[redacted]", message)
    message = re.sub(r"(/accounts/reset/)[^\s]+", r"\1[redacted]", message)
    message = re.sub(r"tx2\.[A-Za-z0-9_-]{43}", "[qr-redacted]", message)
    message = re.sub(r"tx1\.[0-9a-f-]{36}\.[A-Za-z0-9_-]+", "[qr-redacted]", message)
    message = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email-redacted]", message)
    return message


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = redact(record.getMessage()), ()
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Redact after formatting, including exception text and stack information.
        return redact(super().format(record))
