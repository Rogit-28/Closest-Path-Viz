from fastapi import FastAPI
from app.websockets.websockets import socket_app
from app.api.endpoints import router as api_router

app = FastAPI()

app.include_router(api_router, prefix="/api/pathfinding")
app.mount("/ws", socket_app)

@app.get("/")
def read_root():
    return {"message": "Pathfinding Engine is running."}
