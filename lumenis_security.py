"""
Lumenis Security Middleware
============================
Authentication and authorization for protected endpoints.

Usage:
    from lumenis_security import require_auth, verify_ip_allowlist

    @app.post("/api/terminal")
    async def terminal_exec(body: dict, authorized: bool = Depends(require_auth)):
        # Now requires valid bearer token
        ...
"""

import os
from fastapi import Header, HTTPException, Request
from typing import Optional

# Load security configuration from environment
SECURITY_TOKEN = os.environ.get("LUMENIS_SECURITY_TOKEN", "")
ENABLE_TERMINAL_API = os.environ.get("ENABLE_TERMINAL_API", "false").lower() == "true"
ENABLE_NETWORK_PROXY = os.environ.get("ENABLE_NETWORK_PROXY", "false").lower() == "true"
ENABLE_WEBSOCKET_TERMINAL = os.environ.get("ENABLE_WEBSOCKET_TERMINAL", "false").lower() == "true"
TERMINAL_ALLOWED_IPS = os.environ.get("TERMINAL_ALLOWED_IPS", "127.0.0.1,::1").split(",")

# Validation
if not SECURITY_TOKEN or SECURITY_TOKEN == "CHANGE-ME-TO-RANDOM-TOKEN":
    print("⚠️  WARNING: LUMENIS_SECURITY_TOKEN not set or using default!")
    print("   Protected endpoints will reject all requests.")
    print("   Generate a token: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")


async def require_auth(authorization: Optional[str] = Header(None)) -> bool:
    """
    Verify bearer token for protected endpoints.

    Usage:
        from fastapi import Depends
        from lumenis_security import require_auth

        @app.post("/api/protected")
        async def protected_endpoint(authorized: bool = Depends(require_auth)):
            # This code only runs if authorized
            ...

    Raises:
        HTTPException: 401 if no token, 403 if invalid token
    """
    if not SECURITY_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Server security not configured. Contact administrator."
        )

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization required. Include: Authorization: Bearer <token>"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Use: Bearer <token>"
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    if token != SECURITY_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired token"
        )

    return True


async def verify_ip_allowlist(request: Request) -> bool:
    """
    Verify client IP is in the allowlist for terminal access.

    Usage:
        @app.post("/api/terminal")
        async def terminal_exec(
            request: Request,
            body: dict,
            authorized: bool = Depends(require_auth),
            ip_allowed: bool = Depends(verify_ip_allowlist)
        ):
            # Both auth AND IP check passed
            ...

    Raises:
        HTTPException: 403 if IP not allowed
    """
    client_ip = request.client.host

    # Normalize IP (handle IPv6 localhost)
    if client_ip == "::ffff:127.0.0.1":
        client_ip = "127.0.0.1"

    if client_ip not in TERMINAL_ALLOWED_IPS:
        raise HTTPException(
            status_code=403,
            detail=f"Terminal access denied from IP: {client_ip}. Only localhost allowed."
        )

    return True


async def verify_terminal_enabled() -> bool:
    """
    Verify terminal API is enabled in configuration.

    Raises:
        HTTPException: 403 if terminal API is disabled
    """
    if not ENABLE_TERMINAL_API:
        raise HTTPException(
            status_code=403,
            detail="Terminal API is disabled. Set ENABLE_TERMINAL_API=true to enable."
        )
    return True


async def verify_network_proxy_enabled() -> bool:
    """
    Verify network proxy is enabled in configuration.

    Raises:
        HTTPException: 403 if network proxy is disabled
    """
    if not ENABLE_NETWORK_PROXY:
        raise HTTPException(
            status_code=403,
            detail="Network proxy is disabled. Set ENABLE_NETWORK_PROXY=true to enable."
        )
    return True


async def verify_websocket_terminal_enabled() -> bool:
    """
    Verify WebSocket terminal is enabled in configuration.

    Raises:
        HTTPException: 403 if WebSocket terminal is disabled
    """
    if not ENABLE_WEBSOCKET_TERMINAL:
        raise HTTPException(
            status_code=403,
            detail="WebSocket terminal is disabled. Set ENABLE_WEBSOCKET_TERMINAL=true to enable."
        )
    return True


def verify_websocket_token(token: Optional[str]) -> bool:
    """
    Verify token for WebSocket connections.

    Usage:
        @app.websocket("/ws/terminal")
        async def terminal_ws(ws: WebSocket):
            token = ws.query_params.get("token")
            if not verify_websocket_token(token):
                await ws.close(code=403)
                return
            ...

    Returns:
        bool: True if token is valid, False otherwise
    """
    if not SECURITY_TOKEN:
        return False

    if not token:
        return False

    return token == SECURITY_TOKEN


# Security headers middleware
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.

    Add to FastAPI app:
        from fastapi.middleware import Middleware
        from lumenis_security import add_security_headers

        app = FastAPI(middleware=[Middleware(add_security_headers)])
    """
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Don't cache sensitive data
    if "/api/" in request.url.path:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


# Export security status for monitoring
def get_security_status() -> dict:
    """
    Get current security configuration status.

    Returns:
        dict: Security configuration and status
    """
    return {
        "security_token_configured": bool(SECURITY_TOKEN and SECURITY_TOKEN != "CHANGE-ME-TO-RANDOM-TOKEN"),
        "terminal_api_enabled": ENABLE_TERMINAL_API,
        "network_proxy_enabled": ENABLE_NETWORK_PROXY,
        "websocket_terminal_enabled": ENABLE_WEBSOCKET_TERMINAL,
        "terminal_allowed_ips": TERMINAL_ALLOWED_IPS,
        "recommendation": "Disable terminal API and network proxy in production unless absolutely necessary"
    }
