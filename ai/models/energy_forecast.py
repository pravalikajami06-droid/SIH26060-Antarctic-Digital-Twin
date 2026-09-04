import json
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# POLAR — Energy Forecasting Model
# SIH26060 — Antarctic Digital Twin
#
# Uses NumPy linear regression to avoid dependency on
# scikit-learn in the current Windows environment.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "engineered_operational_data.csv"
)

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "energy_forecast.json"


print("=" * 70)
print("POLAR — ENERGY FORECASTING")
print("=" * 70)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)


# ------------------------------------------------------------
# Forecast configuration
# ------------------------------------------------------------

FORECAST_HORIZON = 24
TEST_HORIZON = 24


# ------------------------------------------------------------
# Feature preparation
# ------------------------------------------------------------

def prepare_features(station_df):
    data = station_df.copy()

    data["lag_1"] = (
        data["energy_consumption_kwh"].shift(1)
    )

    data["lag_24"] = (
        data["energy_consumption_kwh"].shift(24)
    )

    data["lag_168"] = (
        data["energy_consumption_kwh"].shift(168)
    )

    data["rolling_6h"] = (
        data["energy_consumption_kwh"]
        .shift(1)
        .rolling(6)
        .mean()
    )

    data["rolling_24h"] = (
        data["energy_consumption_kwh"]
        .shift(1)
        .rolling(24)
        .mean()
    )

    feature_columns = [
        "lag_1",
        "lag_24",
        "lag_168",
        "rolling_6h",
        "rolling_24h",
        "temperature_c",
        "wind_speed_kmh",
        "solar_generation_kw",
        "occupancy",
        "temperature_stress",
        "generator_dependency_percent",
    ]

    data = data.dropna(
        subset=feature_columns + [
            "energy_consumption_kwh"
        ]
    )

    return data, feature_columns


# ------------------------------------------------------------
# NumPy linear regression
# ------------------------------------------------------------

def train_linear_model(X, y):

    # Add intercept column
    X_design = np.column_stack(
        [
            np.ones(len(X)),
            X
        ]
    )

    # Least-squares solution
    coefficients, _, _, _ = np.linalg.lstsq(
        X_design,
        y,
        rcond=None
    )

    return coefficients


def predict_linear_model(coefficients, X):

    X_design = np.column_stack(
        [
            np.ones(len(X)),
            X
        ]
    )

    return X_design @ coefficients


# ------------------------------------------------------------
# Metrics
# ------------------------------------------------------------

def calculate_metrics(actual, predicted):

    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    mae = np.mean(
        np.abs(actual - predicted)
    )

    rmse = np.sqrt(
        np.mean(
            (actual - predicted) ** 2
        )
    )

    denominator = np.where(
        actual == 0,
        1,
        np.abs(actual)
    )

    mape = np.mean(
        np.abs(actual - predicted)
        / denominator
    ) * 100

    return {
        "mae_kwh": round(float(mae), 3),
        "rmse_kwh": round(float(rmse), 3),
        "mape_percent": round(float(mape), 3),
    }


# ------------------------------------------------------------
# Train + test one station
# ------------------------------------------------------------

def forecast_station(station_name, station_df):

    station_df = station_df.copy()

    prepared, feature_columns = prepare_features(
        station_df
    )

    if len(prepared) <= TEST_HORIZON + 100:
        raise ValueError(
            f"Not enough data for {station_name}"
        )

    # --------------------------------------------------------
    # Chronological train/test split
    # --------------------------------------------------------

    train_data = prepared.iloc[:-TEST_HORIZON]

    test_data = prepared.iloc[-TEST_HORIZON:]

    X_train = train_data[feature_columns].to_numpy(
        dtype=float
    )

    y_train = train_data[
        "energy_consumption_kwh"
    ].to_numpy(dtype=float)

    X_test = test_data[feature_columns].to_numpy(
        dtype=float
    )

    y_test = test_data[
        "energy_consumption_kwh"
    ].to_numpy(dtype=float)

    # --------------------------------------------------------
    # Train model
    # --------------------------------------------------------

    coefficients = train_linear_model(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # Test prediction
    # --------------------------------------------------------

    test_predictions = predict_linear_model(
        coefficients,
        X_test
    )

    # Energy cannot be negative
    test_predictions = np.maximum(
        test_predictions,
        0
    )

    metrics = calculate_metrics(
        y_test,
        test_predictions
    )

    # --------------------------------------------------------
    # Train final model using all available data
    # --------------------------------------------------------

    X_all = prepared[
        feature_columns
    ].to_numpy(dtype=float)

    y_all = prepared[
        "energy_consumption_kwh"
    ].to_numpy(dtype=float)

    final_coefficients = train_linear_model(
        X_all,
        y_all
    )

    # --------------------------------------------------------
    # Future 24-hour forecast
    #
    # We use the latest 24 hours of environmental/operational
    # features as the short-term future scenario.
    # --------------------------------------------------------

    history = station_df.copy()

    predictions = []

    last_timestamp = history["timestamp"].iloc[-1]

    future_timestamps = pd.date_range(
        start=last_timestamp + pd.Timedelta(hours=1),
        periods=FORECAST_HORIZON,
        freq="h"
    )

    for i in range(FORECAST_HORIZON):

        current_index = len(history)

        # Repeat recent 24-hour environmental pattern
        source_index = (
            len(station_df) - 24 + i
        )

        source_index = min(
            source_index,
            len(station_df) - 1
        )

        source_row = station_df.iloc[
            source_index
        ]

        # Previous energy values
        lag_1 = (
            history["energy_consumption_kwh"]
            .iloc[-1]
        )

        lag_24 = (
            history["energy_consumption_kwh"]
            .iloc[-24]
        )

        if len(history) >= 168:
            lag_168 = (
                history["energy_consumption_kwh"]
                .iloc[-168]
            )
        else:
            lag_168 = lag_24

        rolling_6h = (
            history["energy_consumption_kwh"]
            .iloc[-6:]
            .mean()
        )

        rolling_24h = (
            history["energy_consumption_kwh"]
            .iloc[-24:]
            .mean()
        )

        temperature = source_row[
            "temperature_c"
        ]

        wind_speed = source_row[
            "wind_speed_kmh"
        ]

        solar_generation = source_row[
            "solar_generation_kw"
        ]

        occupancy = source_row[
            "occupancy"
        ]

        temperature_stress = source_row[
            "temperature_stress"
        ]

        generator_dependency = source_row[
            "generator_dependency_percent"
        ]

        feature_values = np.array([
            lag_1,
            lag_24,
            lag_168,
            rolling_6h,
            rolling_24h,
            temperature,
            wind_speed,
            solar_generation,
            occupancy,
            temperature_stress,
            generator_dependency,
        ], dtype=float).reshape(1, -1)

        prediction = predict_linear_model(
            final_coefficients,
            feature_values
        )[0]

        prediction = max(
            0,
            float(prediction)
        )

        predictions.append(
            round(prediction, 3)
        )

        # Add predicted point to history for recursive lags
        new_row = source_row.copy()

        new_row["timestamp"] = (
            future_timestamps[i]
        )

        new_row[
            "energy_consumption_kwh"
        ] = prediction

        history = pd.concat(
            [
                history,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

    # --------------------------------------------------------
    # Forecast summary
    # --------------------------------------------------------

    forecast_mean = np.mean(predictions)

    forecast_max = np.max(predictions)

    forecast_min = np.min(predictions)

    return {
        "station_id": station_name,
        "model": "NumPy Linear Regression",
        "forecast_horizon_hours": FORECAST_HORIZON,
        "training_records": int(len(train_data)),
        "test_records": int(len(test_data)),
        "test_metrics": metrics,
        "forecast_summary": {
            "mean_energy_kwh": round(
                float(forecast_mean),
                3
            ),
            "minimum_energy_kwh": round(
                float(forecast_min),
                3
            ),
            "maximum_energy_kwh": round(
                float(forecast_max),
                3
            ),
        },
        "forecast": [
            {
                "timestamp": str(
                    future_timestamps[i]
                ),
                "predicted_energy_kwh": predictions[i],
            }
            for i in range(FORECAST_HORIZON)
        ],
    }


# ------------------------------------------------------------
# Run forecasting for Bharati + Maitri
# ------------------------------------------------------------

results = {}

for station_name in sorted(
    df["station_id"].unique()
):

    print()
    print(
        f"Processing station: {station_name}"
    )

    station_df = df[
        df["station_id"] == station_name
    ].copy()

    result = forecast_station(
        station_name,
        station_df
    )

    results[station_name] = result

    print(
        f"Test RMSE : "
        f"{result['test_metrics']['rmse_kwh']} kWh"
    )

    print(
        f"Test MAE  : "
        f"{result['test_metrics']['mae_kwh']} kWh"
    )

    print(
        f"Test MAPE : "
        f"{result['test_metrics']['mape_percent']}%"
    )

    print(
        f"24h mean forecast : "
        f"{result['forecast_summary']['mean_energy_kwh']} kWh"
    )


# ------------------------------------------------------------
# Save JSON
# ------------------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        results,
        file,
        indent=2
    )


# ------------------------------------------------------------
# Final output
# ------------------------------------------------------------

print()
print("=" * 70)
print("ENERGY FORECASTING COMPLETED SUCCESSFULLY")
print("=" * 70)

print()
print(f"Output file:")
print(OUTPUT_FILE)

print()
print("Stations processed:")

for station_name in results:
    print(
        f" - {station_name}: "
        f"{FORECAST_HORIZON}-hour forecast generated"
    )