from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.db import models
from app.db.database import engine

# This will create the database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Graph Data Service is running."}
