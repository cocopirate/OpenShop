import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

log = structlog.get_logger(__name__)

limiter = Limiter(key_func=get_remote_address)


def setup_rate_limiting(app) -> None:
    """Attach slowapi rate-limiter state and error handler to a FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
