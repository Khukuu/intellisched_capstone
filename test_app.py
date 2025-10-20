from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Test app is running"}

@app.get("/status")
async def status():
    return {"status": "ok", "message": "Test app is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
