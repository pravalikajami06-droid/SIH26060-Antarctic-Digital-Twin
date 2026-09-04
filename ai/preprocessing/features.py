import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# POLAR — Feature Engineering Pipeline
# SIH26060 — Antarctic Digital Twin
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "cleaned_operational_data.csv"
)

OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "engineered_operational_data.csv"


print("=" * 70)
print("POLAR — FEATURE ENGINEERING")
print("=" * 70)


# ------------------------------------------------------------
# Load cleaned data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

print(f"Input rows    : {len(df)}")
print(f"Input columns : {len(df.columns)}")


# ------------------------------------------------------------
# Time-based features
# ------------------------------------------------------------

df["hour"] = df["timestamp"].dt.hour

df["day_of_week"] = df["timestamp"].dt.dayofweek

df["day_of_year"] = df["timestamp"].dt.dayofyear

df["month"] = df["timestamp"].dt.month

df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)


# ------------------------------------------------------------
# Temperature stress
#
# Lower temperature means greater heating demand.
# ------------------------------------------------------------

df["temperature_stress"] = np.maximum(
    0,
    -df["temperature_c"] - 5
)


# ------------------------------------------------------------
# Energy balance
#
# Positive = available surplus
# Negative = energy deficit
# ------------------------------------------------------------

df["energy_balance_kw"] = (
    df["solar_generation_kw"]
    + df["generator_output_kw"]
    - df["energy_consumption_kwh"]
)


df["energy_deficit_kw"] = np.maximum(
    0,
    df["energy_consumption_kwh"]
    - df["solar_generation_kw"]
)


# ------------------------------------------------------------
# Renewable contribution
# ------------------------------------------------------------

df["solar_contribution_percent"] = np.where(
    df["energy_consumption_kwh"] > 0,
    (
        df["solar_generation_kw"]
        / df["energy_consumption_kwh"]
        * 100
    ),
    0
)

df["solar_contribution_percent"] = (
    df["solar_contribution_percent"]
    .clip(0, 100)
)


# ------------------------------------------------------------
# Generator dependency
# ------------------------------------------------------------

df["generator_dependency_percent"] = np.where(
    df["energy_consumption_kwh"] > 0,
    (
        df["generator_output_kw"]
        / df["energy_consumption_kwh"]
        * 100
    ),
    0
)

df["generator_dependency_percent"] = (
    df["generator_dependency_percent"]
    .clip(0, 100)
)


# ------------------------------------------------------------
# Battery stress
# ------------------------------------------------------------

df["battery_stress"] = (
    100 - df["battery_level_percent"]
)

df["battery_low_flag"] = (
    df["battery_level_percent"] < 25
).astype(int)


# ------------------------------------------------------------
# Fuel indicators
# ------------------------------------------------------------

df["fuel_low_flag"] = (
    df["fuel_level_liters"] < 3000
).astype(int)

df["fuel_consumption_rate"] = (
    df["fuel_consumption_liters"]
)


# ------------------------------------------------------------
# Water indicators
# ------------------------------------------------------------

df["water_low_flag"] = (
    df["water_level_liters"] < 2000
).astype(int)

df["water_consumption_rate"] = (
    df["water_consumption_liters"]
)


# ------------------------------------------------------------
# Food indicators
# ------------------------------------------------------------

df["food_low_flag"] = (
    df["food_stock_kg"] < 1500
).astype(int)

df["food_consumption_rate"] = (
    df["food_consumption_kg"]
)


# ------------------------------------------------------------
# Generator runtime indicator
# ------------------------------------------------------------

df["generator_active"] = (
    df["generator_output_kw"] > 10
).astype(int)


# ------------------------------------------------------------
# Rolling energy features
#
# Grouped by station so Bharati and Maitri do not mix.
# ------------------------------------------------------------

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)


df["energy_consumption_rolling_6h"] = (
    df.groupby("station_id")["energy_consumption_kwh"]
    .transform(
        lambda x: x.rolling(6, min_periods=1).mean()
    )
)


df["energy_consumption_rolling_24h"] = (
    df.groupby("station_id")["energy_consumption_kwh"]
    .transform(
        lambda x: x.rolling(24, min_periods=1).mean()
    )
)


df["generator_output_rolling_24h"] = (
    df.groupby("station_id")["generator_output_kw"]
    .transform(
        lambda x: x.rolling(24, min_periods=1).mean()
    )
)


# ------------------------------------------------------------
# Rolling environmental features
# ------------------------------------------------------------

df["temperature_rolling_24h"] = (
    df.groupby("station_id")["temperature_c"]
    .transform(
        lambda x: x.rolling(24, min_periods=1).mean()
    )
)


df["wind_rolling_24h"] = (
    df.groupby("station_id")["wind_speed_kmh"]
    .transform(
        lambda x: x.rolling(24, min_periods=1).mean()
    )
)


# ------------------------------------------------------------
# Resource consumption trends
# ------------------------------------------------------------

df["water_consumption_rolling_24h"] = (
    df.groupby("station_id")["water_consumption_liters"]
    .transform(
        lambda x: x.rolling(24, min_periods=1).mean()
    )
)


df["food_consumption_rolling_24h"] = (
    df.groupby("station_id")["food_consumption_kg"]
    .transform(
        lambda x: x.rolling(24, min_periods=1).mean()
    )
)


# ------------------------------------------------------------
# Resource depletion indicators
# ------------------------------------------------------------

df["fuel_depletion_rate"] = (
    df.groupby("station_id")["fuel_level_liters"]
    .diff()
    .abs()
    .fillna(0)
)


df["water_depletion_rate"] = (
    df.groupby("station_id")["water_level_liters"]
    .diff()
    .abs()
    .fillna(0)
)


df["food_depletion_rate"] = (
    df.groupby("station_id")["food_stock_kg"]
    .diff()
    .abs()
    .fillna(0)
)


# ------------------------------------------------------------
# Operational stress score
#
# Explainable score from 0–100.
# ------------------------------------------------------------

temperature_component = np.clip(
    df["temperature_stress"] / 40 * 30,
    0,
    30
)

battery_component = np.clip(
    (100 - df["battery_level_percent"]) / 100 * 30,
    0,
    30
)

generator_component = np.clip(
    df["generator_dependency_percent"] / 100 * 25,
    0,
    25
)

wind_component = np.clip(
    df["wind_speed_kmh"] / 45 * 15,
    0,
    15
)

df["operational_stress_score"] = (
    temperature_component
    + battery_component
    + generator_component
    + wind_component
).clip(0, 100)


# ------------------------------------------------------------
# Replace any numerical infinities
# ------------------------------------------------------------

df = df.replace(
    [np.inf, -np.inf],
    np.nan
)


# ------------------------------------------------------------
# Fill any rolling-start NaN values
# ------------------------------------------------------------

numeric_columns = df.select_dtypes(
    include="number"
).columns

df[numeric_columns] = (
    df[numeric_columns]
    .ffill()
    .bfill()
)


# ------------------------------------------------------------
# Final sorting
# ------------------------------------------------------------

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

print()
print(f"Output rows    : {len(df)}")
print(f"Output columns : {len(df.columns)}")

print()
print("New AI features:")

original_columns = [
    "timestamp",
    "station_id",
    "building_id",
    "temperature_c",
    "wind_speed_kmh",
    "solar_generation_kw",
    "generator_output_kw",
    "energy_consumption_kwh",
    "battery_level_percent",
    "fuel_level_liters",
    "fuel_consumption_liters",
    "water_level_liters",
    "water_consumption_liters",
    "food_stock_kg",
    "food_consumption_kg",
    "occupancy",
    "building_load_kw",
]

new_features = [
    column
    for column in df.columns
    if column not in original_columns
]

for feature in new_features:
    print(f" - {feature}")


print()
print("Missing values:")
print(df.isna().sum().sum())

print()
print("Feature engineering completed successfully.")

print()
print(f"Output file:")
print(OUTPUT_FILE)