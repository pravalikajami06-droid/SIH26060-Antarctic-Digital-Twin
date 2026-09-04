import json
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# POLAR — ANOMALY DETECTION
# SIH26060 — Antarctic Digital Twin
#
# NumPy + Pandas statistical anomaly detection.
# No scikit-learn required.
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

OUTPUT_FILE = OUTPUT_DIR / "anomaly_detection.json"


print("=" * 70)
print("POLAR — ANOMALY DETECTION")
print("=" * 70)


# ------------------------------------------------------------
# Load engineered data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)

print(f"Input rows    : {len(df)}")
print(f"Input columns : {len(df.columns)}")


# ------------------------------------------------------------
# Features used for anomaly detection
# ------------------------------------------------------------

ANOMALY_FEATURES = [
    "energy_consumption_kwh",
    "generator_output_kw",
    "battery_level_percent",
    "fuel_consumption_liters",
    "water_consumption_liters",
    "food_consumption_kg",
    "temperature_c",
    "wind_speed_kmh",
    "solar_generation_kw",
    "building_load_kw",
]


# ------------------------------------------------------------
# Robust anomaly score using Median Absolute Deviation
#
# MAD is less affected by extreme values than standard
# deviation and works well for operational monitoring.
# ------------------------------------------------------------

def robust_z_score(series):

    series = pd.Series(series).astype(float)

    median = series.median()

    mad = np.median(
        np.abs(series - median)
    )

    # Prevent division by zero
    if mad < 1e-9:
        std = series.std()

        if std < 1e-9 or np.isnan(std):
            return pd.Series(
                np.zeros(len(series)),
                index=series.index
            )

        return (
            (series - median)
            / std
        )

    return (
        0.6745
        * (series - median)
        / mad
    )


# ------------------------------------------------------------
# Convert robust z-score into 0–1 anomaly score
# ------------------------------------------------------------

def anomaly_score_from_z(z):

    z = np.abs(z)

    # Approximately:
    # z < 2  -> low concern
    # z = 3  -> moderate
    # z >= 4 -> strong anomaly

    score = (
        (z - 2.0)
        / 3.0
    )

    score = np.clip(
        score,
        0,
        1
    )

    return score


# ------------------------------------------------------------
# Analyze one station
# ------------------------------------------------------------

def analyze_station(station_name, station_df):

    station_df = station_df.copy()

    station_df = station_df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    feature_scores = []

    # --------------------------------------------------------
    # Calculate anomaly score for every feature
    # --------------------------------------------------------

    for feature in ANOMALY_FEATURES:

        z = robust_z_score(
            station_df[feature]
        )

        score = anomaly_score_from_z(z)

        feature_scores.append(score)

        station_df[
            f"{feature}_anomaly_score"
        ] = score

    # --------------------------------------------------------
    # Overall anomaly score
    #
    # Maximum captures serious abnormal behavior while the
    # average prevents a single tiny deviation dominating.
    # --------------------------------------------------------

    score_matrix = np.column_stack(
        feature_scores
    )

    mean_score = np.mean(
        score_matrix,
        axis=1
    )

    max_score = np.max(
        score_matrix,
        axis=1
    )

    overall_score = (
        0.60 * max_score
        + 0.40 * mean_score
    )

    station_df["anomaly_score"] = np.clip(
        overall_score,
        0,
        1
    )

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    station_df["anomaly_level"] = np.select(
        [
            station_df["anomaly_score"] >= 0.75,
            station_df["anomaly_score"] >= 0.45,
        ],
        [
            "ANOMALY",
            "WARNING",
        ],
        default="NORMAL"
    )

    # --------------------------------------------------------
    # Identify the feature responsible for the highest score
    # --------------------------------------------------------

    score_columns = [
        f"{feature}_anomaly_score"
        for feature in ANOMALY_FEATURES
    ]

    station_df["primary_anomaly_feature"] = (
        station_df[score_columns]
        .idxmax(axis=1)
        .str.replace(
            "_anomaly_score",
            "",
            regex=False
        )
    )

    # --------------------------------------------------------
    # Count levels
    # --------------------------------------------------------

    normal_count = int(
        (
            station_df["anomaly_level"]
            == "NORMAL"
        ).sum()
    )

    warning_count = int(
        (
            station_df["anomaly_level"]
            == "WARNING"
        ).sum()
    )

    anomaly_count = int(
        (
            station_df["anomaly_level"]
            == "ANOMALY"
        ).sum()
    )

    # --------------------------------------------------------
    # Overall station statistics
    # --------------------------------------------------------

    highest_score = float(
        station_df["anomaly_score"].max()
    )

    average_score = float(
        station_df["anomaly_score"].mean()
    )

    # --------------------------------------------------------
    # Keep only important output fields
    # --------------------------------------------------------

    output_columns = [
        "timestamp",
        "station_id",
        "building_id",
        "energy_consumption_kwh",
        "generator_output_kw",
        "battery_level_percent",
        "fuel_level_liters",
        "water_level_liters",
        "food_stock_kg",
        "temperature_c",
        "wind_speed_kmh",
        "solar_generation_kw",
        "building_load_kw",
        "anomaly_score",
        "anomaly_level",
        "primary_anomaly_feature",
    ]

    records = station_df[
        output_columns
    ].copy()

    records["timestamp"] = (
        records["timestamp"]
        .astype(str)
    )

    # --------------------------------------------------------
    # Convert records to JSON-safe format
    # --------------------------------------------------------

    records = records.replace(
        [np.inf, -np.inf],
        np.nan
    )

    records = records.where(
        pd.notna(records),
        None
    )

    return {
        "station_id": station_name,
        "records_analyzed": int(
            len(station_df)
        ),
        "normal_records": normal_count,
        "warning_records": warning_count,
        "anomaly_records": anomaly_count,
        "average_anomaly_score": round(
            average_score,
            4
        ),
        "highest_anomaly_score": round(
            highest_score,
            4
        ),
        "detection_method": (
            "Robust Median Absolute Deviation "
            "statistical detector"
        ),
        "records": records.to_dict(
            orient="records"
        ),
    }


# ------------------------------------------------------------
# Run detection for all stations
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

    result = analyze_station(
        station_name,
        station_df
    )

    results[station_name] = result

    print(
        f"Records analyzed : "
        f"{result['records_analyzed']}"
    )

    print(
        f"Normal records   : "
        f"{result['normal_records']}"
    )

    print(
        f"Warning records  : "
        f"{result['warning_records']}"
    )

    print(
        f"Anomaly records  : "
        f"{result['anomaly_records']}"
    )

    print(
        f"Average score    : "
        f"{result['average_anomaly_score']}"
    )

    print(
        f"Highest score    : "
        f"{result['highest_anomaly_score']}"
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
# Final verification
# ------------------------------------------------------------

total_records = sum(
    result["records_analyzed"]
    for result in results.values()
)

total_anomalies = sum(
    result["anomaly_records"]
    for result in results.values()
)

total_warnings = sum(
    result["warning_records"]
    for result in results.values()
)


print()
print("=" * 70)
print("ANOMALY DETECTION COMPLETED SUCCESSFULLY")
print("=" * 70)

print()
print(f"Total records analyzed : {total_records}")
print(f"Total warnings         : {total_warnings}")
print(f"Total anomalies        : {total_anomalies}")

print()
print("Output file:")
print(OUTPUT_FILE)

print()
print("Stations processed:")

for station_name in results:
    print(
        f" - {station_name}: "
        f"{results[station_name]['records_analyzed']} records"
    )