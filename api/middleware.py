import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.middleware")

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track API performance and detect slow requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip monitoring for health endpoint to avoid overhead
        if request.url.path == "/health":
            return await call_next(request)
        
        start_time = time.time()
        
        # Track request info
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # Calculate timing
        process_time = time.time() - start_time
        
        # Log slow requests (>1 second)
        if process_time > 1.0:
            logger.warning(f"SLOW REQUEST: {method} {url} - {process_time:.3f}s - IP: {client_ip}")
        elif process_time > 0.5:
            logger.info(f"SLOW REQUEST: {method} {url} - {process_time:.3f}s - IP: {client_ip}")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class DatabaseConnectionMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure database connections are properly handled"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log database-related errors
            if "database" in str(e).lower() or "connection" in str(e).lower():
                logger.error(f"Database error in {request.method} {request.url}: {e}")
            raise
        finally:
            # Log timing for database operations
            process_time = time.time() - start_time
            if process_time > 2.0:
                logger.warning(f"Very slow request: {request.method} {request.url} - {process_time:.3f}s")