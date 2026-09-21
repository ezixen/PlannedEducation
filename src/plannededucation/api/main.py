import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models, routes_auth, routes_exam, routes_chat, routes_anonymizer, routes_parent

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Planned Education API",
    description="Backend for the Planned Education app.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(routes_auth.router)
app.include_router(routes_exam.router)
app.include_router(routes_chat.router)
app.include_router(routes_anonymizer.router)
app.include_router(routes_parent.router)

# CORS is deliberately explicit: credentialed requests cannot be safely served
# to arbitrary origins.
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Planned Education API is running"}

