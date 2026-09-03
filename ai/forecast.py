import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression


def load_weather_data(station: str) -> pd.DataFrame:
    if station.lower() == "bharati":
        file_path = Path("data/raw/Bharati - AWS_2026_filtered_data.xlsx")
    elif station.lower() == "maitri":
        file_path = Path("data/raw/Maitri - AWS_2016_filtered_data.xlsx")
    else:
        raise ValueError("Station must be Bharati or Maitri")

    df = pd.read_excel(file_path)
    df["obstime"] = pd.to_datetime(df["obstime"])
    df = df.sort_values("obstime")

    return df


def forecast_temperature(station: str, forecast_points: int = 24):
    df = load_weather_data(station)

    temperature = df[["obstime", "tempr"]].dropna().copy()

    # Use the most recent observations
    recent = temperature.tail(500).copy()

    recent["time_index"] = np.arange(len(recent))

    X = recent[["time_index"]]
    y = recent["tempr"]

    model = LinearRegression()
    model.fit(X, y)

    future_index = np.arange(
        len(recent),
        len(recent) + forecast_points
    ).reshape(-1, 1)

    predictions = model.predict(future_index)

    interval = (
        recent["obstime"].iloc[-1]
        - recent["obstime"].iloc[-2]
    )

    future_times = [
        recent["obstime"].iloc[-1] + interval * (i + 1)
        for i in range(forecast_points)
    ]

    forecast = pd.DataFrame({
        "timestamp": future_times,
        "predicted_temperature_c": predictions.round(2)
    })

    return forecast


if __name__ == "__main__":

    for station in ["Bharati", "Maitri"]:

        print(f"\n{'=' * 50}")
        print(f"{station} TEMPERATURE FORECAST")
        print(f"{'=' * 50}")

        forecast = forecast_temperature(station, 24)

        print(forecast.to_string(index=False))