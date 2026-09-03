import pandas as pd
from pathlib import Path

from sqlalchemy import text

from database import engine


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"


FILES = {
    "Bharati": DATA_DIR / "Bharati - AWS_2026_filtered_data.xlsx",
    "Maitri": DATA_DIR / "Maitri - AWS_2016_filtered_data.xlsx",
}


def load_station_data(station, file_path):
    print(f"\nLoading {station} data...")

    df = pd.read_excel(file_path)

    df = df.rename(columns={
        "obstime": "observation_time",
        "tempr": "temperature_c",
        "ap": "air_pressure_hpa",
        "ws": "wind_speed",
        "wd": "wind_direction",
        "rh": "relative_humidity"
    })

    df["station"] = station

    df = df[
        [
            "station",
            "observation_time",
            "temperature_c",
            "air_pressure_hpa",
            "wind_speed",
            "wind_direction",
            "relative_humidity"
        ]
    ]

    df.to_sql(
        "weather_observations",
        engine,
        if_exists="append",
        index=False,
        chunksize=5000
    )

    print(f"{station}: {len(df)} records inserted successfully.")


def main():
    for station, file_path in FILES.items():
        load_station_data(station, file_path)

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM weather_observations")
        )
        total = result.scalar()

    print(f"\nTotal records in database: {total}")


if __name__ == "__main__":
    main()