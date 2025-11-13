from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.graph import create_graph_from_osm
from app.db import crud
from app.db.database import SessionLocal

router = APIRouter()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/graphs/")
async def create_graph_and_save(place_name: str, db: Session = Depends(get_db)):
    """
    Creates a graph from OpenStreetMap data for a given place and saves it to the database.
    """
    graph = create_graph_from_osm(place_name)
    db_graph = crud.create_graph(db=db, place_name=place_name, graph=graph)
    return {"message": f"Graph for {place_name} created and saved with id {db_graph.id}."}

@router.get("/graphs/{place_name}")
async def get_graph(place_name: str, db: Session = Depends(get_db)):
    """
    Retrieves a graph by its place name.
    """
    db_graph = crud.get_graph_by_place_name(db=db, place_name=place_name)
    if db_graph is None:
        return {"error": "Graph not found"}
    return db_graph
