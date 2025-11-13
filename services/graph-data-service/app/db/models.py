from sqlalchemy import Column, Integer, String, JSON
from geoalchemy2 import Geometry
from app.db.database import Base

class Graph(Base):
    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True, index=True)
    place_name = Column(String, unique=True, index=True)
    graph_data = Column(JSON)
    bounding_box = Column(Geometry(geometry_type='POLYGON', srid=4326))
