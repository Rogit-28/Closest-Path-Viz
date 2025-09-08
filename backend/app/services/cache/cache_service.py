"""
Cache management service — handles graph caching, refresh scheduling, and approval workflows.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("pathfinding.cache")

# Top 100 cities by population (subset for initial implementation)
TOP_CITIES = [
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "country": "JP"},
    {"name": "Delhi", "lat": 28.7041, "lon": 77.1025, "country": "IN"},
    {"name": "Shanghai", "lat": 31.2304, "lon": 121.4737, "country": "CN"},
    {"name": "São Paulo", "lat": -23.5505, "lon": -46.6333, "country": "BR"},
    {"name": "Mexico City", "lat": 19.4326, "lon": -99.1332, "country": "MX"},
    {"name": "Cairo", "lat": 30.0444, "lon": 31.2357, "country": "EG"},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777, "country": "IN"},
    {"name": "Beijing", "lat": 39.9042, "lon": 116.4074, "country": "CN"},
    {"name": "Dhaka", "lat": 23.8103, "lon": 90.4125, "country": "BD"},
    {"name": "Osaka", "lat": 34.6937, "lon": 135.5023, "country": "JP"},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "country": "US"},
    {"name": "Karachi", "lat": 24.8607, "lon": 67.0011, "country": "PK"},
    {"name": "Buenos Aires", "lat": -34.6037, "lon": -58.3816, "country": "AR"},
    {"name": "Istanbul", "lat": 41.0082, "lon": 28.9784, "country": "TR"},
    {"name": "Kolkata", "lat": 22.5726, "lon": 88.3639, "country": "IN"},
    {"name": "Lagos", "lat": 6.5244, "lon": 3.3792, "country": "NG"},
    {"name": "Manila", "lat": 14.5995, "lon": 120.9842, "country": "PH"},
    {"name": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729, "country": "BR"},
    {"name": "Guangzhou", "lat": 23.1291, "lon": 113.2644, "country": "CN"},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "country": "US"},
    {"name": "Moscow", "lat": 55.7558, "lon": 37.6173, "country": "RU"},
    {"name": "Shenzhen", "lat": 22.5431, "lon": 114.0579, "country": "CN"},
    {"name": "Lahore", "lat": 31.5497, "lon": 74.3436, "country": "PK"},
    {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946, "country": "IN"},
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"},
    {"name": "Jakarta", "lat": -6.2088, "lon": 106.8456, "country": "ID"},
    {"name": "Chennai", "lat": 13.0827, "lon": 80.2707, "country": "IN"},
    {"name": "Lima", "lat": -12.0464, "lon": -77.0428, "country": "PE"},
    {"name": "Bangkok", "lat": 13.7563, "lon": 100.5018, "country": "TH"},
    {"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB"},
    {"name": "Seoul", "lat": 37.5665, "lon": 126.9780, "country": "KR"},
    {"name": "Tehran", "lat": 35.6892, "lon": 51.3890, "country": "IR"},
    {"name": "Ho Chi Minh City", "lat": 10.8231, "lon": 106.6297, "country": "VN"},
    {"name": "Hong Kong", "lat": 22.3193, "lon": 114.1694, "country": "HK"},
    {"name": "Baghdad", "lat": 33.3152, "lon": 44.3661, "country": "IQ"},
    {"name": "Riyadh", "lat": 24.7136, "lon": 46.6753, "country": "SA"},
    {"name": "Singapore", "lat": 1.3521, "lon": 103.8198, "country": "SG"},
    {"name": "Santiago", "lat": -33.4489, "lon": -70.6693, "country": "CL"},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093, "country": "AU"},
    {"name": "Toronto", "lat": 43.6532, "lon": -79.3832, "country": "CA"},
    {"name": "Berlin", "lat": 52.5200, "lon": 13.4050, "country": "DE"},
    {"name": "Madrid", "lat": 40.4168, "lon": -3.7038, "country": "ES"},
    {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "country": "US"},
    {"name": "Houston", "lat": 29.7604, "lon": -95.3698, "country": "US"},
    {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194, "country": "US"},
    {"name": "Dubai", "lat": 25.2048, "lon": 55.2708, "country": "AE"},
    {"name": "Rome", "lat": 41.9028, "lon": 12.4964, "country": "IT"},
    {"name": "Amsterdam", "lat": 52.3676, "lon": 4.9041, "country": "NL"},
    {"name": "Kuala Lumpur", "lat": 3.1390, "lon": 101.6869, "country": "MY"},
    {"name": "Nairobi", "lat": -1.2921, "lon": 36.8219, "country": "KE"},
]

# Schedule durations
SCHEDULE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
    "manual": None,
}


class CacheManager:
    """Manages graph cache lifecycle and refresh scheduling."""

    def __init__(self):
        self._schedules: dict[str, dict] = {}
        self._pending_approvals: dict[str, dict] = {}

    def get_cities_list(self) -> list[dict]:
        """Get list of all pre-configured cities."""
        return TOP_CITIES

    def get_schedule(self, city_name: str) -> dict:
        """Get refresh schedule for a city."""
        return self._schedules.get(
            city_name,
            {
                "schedule_type": "weekly",
                "prompt_on_refresh": True,
                "auto_approve_after_days": 7,
                "last_refresh": None,
                "next_refresh": None,
                "pending_approval": False,
            },
        )

    def set_schedule(
        self,
        city_name: str,
        schedule_type: str,
        prompt_on_refresh: bool = True,
        auto_approve_after_days: int = 7,
    ):
        """Set refresh schedule for a city."""
        now = datetime.now(timezone.utc)
        interval = SCHEDULE_INTERVALS.get(schedule_type)
        next_refresh = now + interval if interval else None

        self._schedules[city_name] = {
            "schedule_type": schedule_type,
            "prompt_on_refresh": prompt_on_refresh,
            "auto_approve_after_days": auto_approve_after_days,
            "last_refresh": now.isoformat(),
            "next_refresh": next_refresh.isoformat() if next_refresh else None,
            "pending_approval": False,
        }
        return self._schedules[city_name]

    def get_cities_due_for_refresh(self) -> list[dict]:
        """Get cities whose cache needs refreshing."""
        now = datetime.now(timezone.utc)
        due = []
        for city_name, schedule in self._schedules.items():
            if schedule["next_refresh"] is None:
                continue
            next_refresh = datetime.fromisoformat(schedule["next_refresh"])
            if now >= next_refresh and not schedule["pending_approval"]:
                due.append({"name": city_name, **schedule})
        return due

    def request_refresh(self, city_name: str) -> dict:
        """Request a cache refresh (sets pending approval if needed)."""
        schedule = self.get_schedule(city_name)
        if schedule["prompt_on_refresh"]:
            if city_name not in self._schedules:
                self._schedules[city_name] = schedule
            self._schedules[city_name]["pending_approval"] = True
            return {"status": "pending_approval", "city": city_name}
        return {"status": "approved", "city": city_name}

    def approve_refresh(self, city_name: str) -> dict:
        """Approve a pending refresh."""
        if city_name in self._schedules:
            self._schedules[city_name]["pending_approval"] = False
            now = datetime.now(timezone.utc)
            self._schedules[city_name]["last_refresh"] = now.isoformat()
            interval = SCHEDULE_INTERVALS.get(
                self._schedules[city_name]["schedule_type"]
            )
            if interval:
                self._schedules[city_name]["next_refresh"] = (
                    now + interval
                ).isoformat()
        return {"status": "approved", "city": city_name}

    def defer_refresh(self, city_name: str, defer_days: int = 7) -> dict:
        """Defer a pending refresh."""
        if city_name in self._schedules:
            self._schedules[city_name]["pending_approval"] = False
            next_refresh = datetime.now(timezone.utc) + timedelta(days=defer_days)
            self._schedules[city_name]["next_refresh"] = next_refresh.isoformat()
        return {"status": "deferred", "city": city_name, "defer_days": defer_days}


# Singleton
cache_manager = CacheManager()
