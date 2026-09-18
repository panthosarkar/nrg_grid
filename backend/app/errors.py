import re
from urllib.parse import quote


class EnergyError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)



def safe_provider_message(message: str, key: str, notes: list[str] = ()) -> str:
    """Redact credentials and echoed operator notes before diagnostic logging."""
    for value in (key, *notes):
        if value:
            message = message.replace(value, '[REDACTED]')
            message = message.replace(quote(value, safe=''), '[REDACTED]')
    message = re.sub(r'AIza[\w-]+', '[REDACTED]', message)
    return message[:2000]
