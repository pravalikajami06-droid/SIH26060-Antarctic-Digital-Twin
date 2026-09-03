from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from backend.database import engine
from ai.anomaly import detect_anomalies
from ai.forecast import forecast_temperature


app = FastAPI(
    title="Antarctic Digital Twin API",
    description="Backend API for Maitri and Bharati Antarctic Research Stations using real NCPOR weather data",
    version="2.0.0"
)


VALID_STATIONS = {
    "bharati": "Bharati",
    "maitri": "Maitri"
}


def normalize_station(station: str) -> str:
    key = station.lower()

    if key not in VALID_STATIONS:
        raise HTTPException(
            status_code=404,
            detail="Station must be Bharati or Maitri"
        )

    return VALID_STATIONS[key]


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Antarctic Digital Twin API is running",
        "version": "2.0.0",
        "stations": [
            "Bharati",
            "Maitri"
        ],
        "features": [
            "Weather data",
            "Weather summary",
            "Anomaly detection",
            "Temperature forecasting"
        ]
    }


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

@app.get("/database")
def database_check():

    with engine.connect() as connection:

        result = connection.execute(
            text(
                "SELECT COUNT(*) "
                "FROM weather_observations"
            )
        )

        count = result.scalar()

    return {
        "database": "connected",
        "weather_observations": count
    }


# ---------------------------------------------------------
# WEATHER DATA
# ---------------------------------------------------------

@app.get("/weather/{station}")
def get_weather(
    station: str,
    limit: int = 20
):

    station = normalize_station(station)

    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limit must be greater than 0"
        )

    if limit > 500:
        limit = 500

    query = text(
        """
        SELECT
            id,
            station,
            observation_time,
            temperature_c,
            air_pressure_hpa,
            wind_speed,
            wind_direction,
            relative_humidity,
            created_at
        FROM weather_observations
        WHERE station = :station
        ORDER BY observation_time DESC
        LIMIT :limit
        """
    )

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "station": station,
                "limit": limit
            }
        )

        data = [
            dict(row)
            for row in result.mappings().all()
        ]

    return {
        "station": station,
        "count": len(data),
        "data": data
    }


# ---------------------------------------------------------
# WEATHER SUMMARY
# ---------------------------------------------------------

@app.get("/weather/{station}/summary")
def weather_summary(station: str):

    station = normalize_station(station)

    query = text(
        """
        SELECT
            COUNT(*) AS count,

            ROUND(
                AVG(temperature_c)::numeric,
                2
            ) AS avg_temperature,

            MIN(temperature_c)
                AS min_temperature,

            MAX(temperature_c)
                AS max_temperature,

            ROUND(
                AVG(air_pressure_hpa)::numeric,
                2
            ) AS avg_pressure,

            ROUND(
                AVG(wind_speed)::numeric,
                2
            ) AS avg_wind_speed,

            ROUND(
                AVG(relative_humidity)::numeric,
                2
            ) AS avg_humidity

        FROM weather_observations

        WHERE station = :station
        """
    )

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {"station": station}
        ).mappings().first()

    return {
        "station": station,
        "summary": dict(result)
    }


# ---------------------------------------------------------
# AI ANOMALY DETECTION
# ---------------------------------------------------------

@app.get("/ai/anomaly/{station}")
def ai_anomaly(
    station: str,
    sample_size: int = 5000
):

    station = normalize_station(station)

    if sample_size < 100:
        sample_size = 100

    if sample_size > 20000:
        sample_size = 20000

    try:

        result = detect_anomalies(
            station,
            sample_size=sample_size
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Anomaly detection failed: {error}"
        )


# ---------------------------------------------------------
# AI TEMPERATURE FORECAST
# ---------------------------------------------------------

@app.get("/ai/forecast/{station}")
def ai_forecast(
    station: str,
    forecast_points: int = 24
):

    station = normalize_station(station)

    if forecast_points < 1:
        forecast_points = 1

    if forecast_points > 168:
        forecast_points = 168

    try:

        forecast = forecast_temperature(
            station,
            forecast_points=forecast_points
        )

        data = []

        for _, row in forecast.iterrows():

            data.append(
                {
                    "timestamp": row["timestamp"].isoformat(),
                    "predicted_temperature_c": float(
                        row["predicted_temperature_c"]
                    )
                }
            )

        return {
            "station": station,
            "forecast_type": "baseline_linear_regression",
            "forecast_points": len(data),
            "data": data
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Temperature forecast failed: {error}"
        )


# ---------------------------------------------------------
# AI INSIGHTS
# ---------------------------------------------------------

@app.get("/ai/insights/{station}")
def ai_insights(station: str):

    station = normalize_station(station)

    try:

        anomaly_result = detect_anomalies(
            station,
            sample_size=5000
        )

        forecast = forecast_temperature(
            station,
            forecast_points=24
        )

        anomaly_count = (
            anomaly_result["anomalies_detected"]
        )

        if anomaly_count == 0:
            risk_level = "LOW"

        elif anomaly_count <= 50:
            risk_level = "MEDIUM"

        else:
            risk_level = "HIGH"

        forecast_values = (
            forecast[
                "predicted_temperature_c"
            ]
            .astype(float)
            .tolist()
        )

        return {
            "station": station,

            "risk_level": risk_level,

            "anomaly_detection": {
                "records_analyzed":
                    anomaly_result["records_analyzed"],

                "anomalies_detected":
                    anomaly_count
            },

            "temperature_forecast": {
                "next_24_points":
                    forecast_values
            },

            "recommendation": (
                "Continue routine monitoring."
                if risk_level == "LOW"
                else
                "Review environmental conditions "
                "and investigate detected anomalies."
            )
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"AI insights failed: {error}"
        )