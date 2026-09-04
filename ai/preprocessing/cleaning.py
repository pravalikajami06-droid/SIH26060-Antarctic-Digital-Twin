import pandas as pd
from pathlib import Path


# ============================================================
# POLAR — Data Cleaning Pipeline
# SIH26060 — Antarctic Digital Twin
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "raw" / "antarctic_operational_data.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "cleaned_operational_data.csv"


print("=" * 70)
print("POLAR — DATA CLEANING")
print("=" * 70)

# ------------------------------------------------------------
# Load dataset
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print(f"Input rows    : {len(df)}")
print(f"Input columns : {len(df.columns)}")

# ------------------------------------------------------------
# Convert timestamp
# ------------------------------------------------------------

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

# ------------------------------------------------------------
# Remove duplicate records
# ------------------------------------------------------------

duplicates_before = df.duplicated().sum()

df = df.drop_duplicates()

duplicates_removed = duplicates_before - df.duplicated().sum()

# ------------------------------------------------------------
# Required columns
# ------------------------------------------------------------

required_columns = [
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

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

# ------------------------------------------------------------
# Handle missing values
# ------------------------------------------------------------

missing_before = df.isna().sum().sum()

numeric_columns = df.select_dtypes(
    include="number"
).columns

df[numeric_columns] = (
    df[numeric_columns]
    .interpolate(method="linear")
    .ffill()
    .bfill()
)

missing_after = df.isna().sum().sum()

# ------------------------------------------------------------
# Remove impossible values
# ------------------------------------------------------------

df = df[df["wind_speed_kmh"] >= 0]

df["solar_generation_kw"] = (
    df["solar_generation_kw"].clip(lower=0)
)

df["generator_output_kw"] = (
    df["generator_output_kw"].clip(lower=0)
)

df["energy_consumption_kwh"] = (
    df["energy_consumption_kwh"].clip(lower=0)
)

df["battery_level_percent"] = (
    df["battery_level_percent"].clip(0, 100)
)

df["fuel_level_liters"] = (
    df["fuel_level_liters"].clip(lower=0)
)

df["water_level_liters"] = (
    df["water_level_liters"].clip(lower=0)
)

df["food_stock_kg"] = (
    df["food_stock_kg"].clip(lower=0)
)

df["occupancy"] = (
    df["occupancy"].clip(lower=0)
    .round()
    .astype(int)
)

# ------------------------------------------------------------
# Sort chronologically
# ------------------------------------------------------------

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)

# ------------------------------------------------------------
# Final validation
# ------------------------------------------------------------

if df["timestamp"].isna().any():
    raise ValueError("Invalid timestamp values remain.")

if df["station_id"].isna().any():
    raise ValueError("Missing station IDs remain.")

# ------------------------------------------------------------
# Save cleaned dataset
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

print()
print(f"Duplicates removed : {duplicates_removed}")
print(f"Missing before     : {missing_before}")
print(f"Missing after      : {missing_after}")
print(f"Final rows         : {len(df)}")
print(f"Final columns      : {len(df.columns)}")

print()
print("Stations:")
print(df["station_id"].value_counts())

print()
print("Final missing values:")
print(df.isna().sum())

print()
print(f"Output file:")
print(OUTPUT_FILE)

print()
print("DATA CLEANING COMPLETED SUCCESSFULLY.")