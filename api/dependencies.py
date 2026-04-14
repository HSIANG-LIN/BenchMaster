# ~/benchmaster/api/dependencies.py

import os
from fastapi import Header, HTTPException, status

# In a production environment, this would be loaded from a secure .env file or secret manager
AGENT_AUTH_TOKEN = os.getenv("AGENT_AUTH_TOKEN", "BM-AGENT-DEFAULT-SECRET-2026")

async def verify_agent_token(x_agent_token: str = Header(None)):
    """
    Dependency to verify the X-Agent-Token header for Agent-to-API communication.
    """
    if x_agent_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Agent-Token header",
        )
    
    if x_agent_token != AGENT_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Agent Authentication Token",
        )
    
    return x_agent_token
