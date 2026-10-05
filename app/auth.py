from fastapi import Header, HTTPException
from .settings import settings

def require_admin(x_admin_token: str | None = Header(default=None)):
    # Development may run without a token. Production must always be protected.
    if settings.environment.lower() == 'production' and not settings.admin_token:
        raise HTTPException(status_code=503, detail='ADMIN_TOKEN_not_configured')
    if settings.admin_token and x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail='Unauthorized')
