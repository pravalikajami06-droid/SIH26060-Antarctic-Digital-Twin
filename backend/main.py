from fastapi import FastAPI
from sqlalchemy import text

from backend.database import engine


app = FastAPI(
    title="Antarctic Digital Twin API",
    description="Backend API for Maitri and Bharati Antarctic Research Stations",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Antarctic Digital Twin API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/database")
def database_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT COUNT(*) FROM weather_observations"))
        count = result.scalar()

    return {
        "database": "connected",
        "weather_observations": count
    }
@app.get("/weather/{station}")
def get_weather(station: str, limit: int = 20):
    query = text("""
        SELECT *
        FROM weather_observations
        WHERE station = :station
        ORDER BY observation_time DESC
        LIMIT :limit
    """)

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {"station": station, "limit": limit}
        )

        data = [dict(row) for row in result.mappings().all()]

    return {
        "station": station,
        "count": len(data),
        "data": data
    }