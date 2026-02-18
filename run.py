import uvicorn
from backend.config import HOST, PORT, DEBUG

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info",
    )
