from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models, routes_auth, routes_exam, routes_chat

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PlannedEducation API",
    description="Backend for the PlannedEducation app.",
    version="1.0.0",
)

app.include_router(routes_auth.router)
app.include_router(routes_exam.router)
app.include_router(routes_chat.router)

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "PlannedEducation API is running"}

