# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.docker_routes import router as docker_router
from app.api.proxmox_routes import router as proxmox_router
from app.api.user_routes import router as user_router
from app.api.auth import get_api_key
from app.core.config import get_settings
import logging
from datetime import datetime

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CloudFaster API",
    description="API for CloudFaster services",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_router, tags=["User Registration"])
app.include_router(docker_router, tags=["Docker Services"])
app.include_router(proxmox_router, tags=["Proxmox VMs"])

@app.get("/")
async def root():
    return {"message": "Welcome to CloudFaster API"}

@app.get("/heartbeat")
async def heartbeat():
    """Check if the API is running"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/protected", dependencies=[Depends(get_api_key)])
async def protected():
    """Protected endpoint that requires API key authentication"""
    return {
        "status": "success",
        "message": "You have access to protected endpoints",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)