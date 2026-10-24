import os
import sys
import time

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import auth, admin, documents, requests
from logger import logger

# Initialize database schema, indexes, and master administrator
try:
    init_db()
except Exception as e:
    logger.error(f"Error during database startup initialization: {e}")

app = FastAPI(
    title="Trust Vault Enterprise API",
    description="Secure Enterprise Cloud Document Vault and Whitelist Access Management",
    version="2.0.0"
)

# Request logging and timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"Completed Request: {request.method} {request.url.path} -> Status {response.status_code} ({process_time:.2f}ms)")
        return response
    except Exception as exc:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc} ({process_time:.2f}ms)")
        raise

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all feature routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(requests.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Trust Vault Enterprise API",
        "version": "2.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for cloud load balancers, orchestrators, and uptime monitors."""
    return {"status": "healthy", "timestamp": time.time()}
