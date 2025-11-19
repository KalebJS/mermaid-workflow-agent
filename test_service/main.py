"""
Simple test service to verify Railway deployment
"""
from fastapi import FastAPI

app = FastAPI(title="Test Service")


@app.get("/")
async def root():
    return {"message": "Test service is running!"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
