from fastapi import FastAPI
import os

app = FastAPI(title="AlphaAgent API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to AlphaAgent AI Trading API"}

@app.get("/health")
def health_check():
    # נשלוף את משתנה הסביבה של הדאטה-בייס כדי לוודא שהוא מוזרק לקוד
    db_url = os.getenv("DATABASE_URL", "Not Connected")
    
    return {
        "status": "healthy",
        "database_status": "configured" if db_url != "Not Connected" else "missing",
        "environment": "production" if os.getenv("RENDER") else "development"
    }