from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.core.database import Base


class CachedGraph(Base):
    __tablename__ = "cached_graphs"

    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String(255), nullable=False, index=True)
    country_code = Column(String(10), nullable=True)
    bbox_north = Column(Float, nullable=False)
    bbox_south = Column(Float, nullable=False)
    bbox_east = Column(Float, nullable=False)
    bbox_west = Column(Float, nullable=False)
    center_point = Column(Geometry("POINT", srid=4326), nullable=True)
    node_count = Column(Integer, nullable=False, default=0)
    edge_count = Column(Integer, nullable=False, default=0)
    graph_data = Column(Text, nullable=True)  # serialized adjacency list JSON
    graph_file_path = Column(String(512), nullable=True)
    fallback_speed_pct = Column(Float, nullable=True, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class CacheSchedule(Base):
    __tablename__ = "cache_schedules"

    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String(255), nullable=False, index=True)
    schedule_type = Column(
        String(50), nullable=False, default="weekly"
    )  # daily/weekly/biweekly/monthly/manual
    prompt_on_refresh = Column(Boolean, default=True)
    auto_approve_after_days = Column(Integer, default=7)
    defer_max_days = Column(Integer, default=7)
    last_refresh = Column(DateTime(timezone=True), nullable=True)
    next_refresh = Column(DateTime(timezone=True), nullable=True)
    pending_approval = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    settings_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PathfindingResult(Base):
    __tablename__ = "pathfinding_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)
    start_lat = Column(Float, nullable=False)
    start_lon = Column(Float, nullable=False)
    end_lat = Column(Float, nullable=False)
    end_lon = Column(Float, nullable=False)
    path_nodes = Column(JSON, nullable=True)
    path_length_km = Column(Float, nullable=True)
    nodes_explored = Column(Integer, nullable=True)
    computation_time_ms = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
