import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# POLAR — Synthetic Antarctic Operational Dataset Generator
# SIH26060 — Antarctic Digital Twin
# ============================================================

SEED = 26060
rng = np.random.default_rng(SEED)

OUTPUT_DIR = Path(__file__).resolve().parent / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "antarctic_operational_data.csv"


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

START_DATE = "2026-03-01"
PERIODS = 180 * 24       # 180 days, hourly observations

stations = {
    "Bharati": {
        "base_temperature": -18.0,
        "temperature_variation": 8.0,
        "base_occupancy": 32,
        "solar_capacity": 180.0,
        "generator_capacity": 420.0,
        "battery_capacity": 1200.0,
        "fuel_capacity": 18000.0,
        "water_capacity": 12000.0,
        "food_capacity": 9000.0,
    },
    "Maitri": {
        "base_temperature": -21.0,
        "temperature_variation": 9.0,
        "base_occupancy": 28,
        "solar_capacity": 150.0,
        "generator_capacity": 380.0,
        "battery_capacity": 1000.0,
        "fuel_capacity": 16000.0,
        "water_capacity": 10500.0,
        "food_capacity": 8000.0,
    },
}


# ------------------------------------------------------------
# Generate one station
# ------------------------------------------------------------

def generate_station_data(station_name, config):

    timestamps = pd.date_range(
        start=START_DATE,
        periods=PERIODS,
        freq="h"
    )

    n = len(timestamps)

    hour = timestamps.hour.to_numpy()
    day_of_year = timestamps.dayofyear.to_numpy()

    # --------------------------------------------------------
    # Environmental conditions
    # --------------------------------------------------------

    seasonal_temperature = (
        config["base_temperature"]
        + config["temperature_variation"]
        * np.sin(2 * np.pi * day_of_year / 365.25)
    )

    daily_temperature = (
        3.0 * np.sin(2 * np.pi * (hour - 6) / 24)
    )

    temperature = (
        seasonal_temperature
        + daily_temperature
        + rng.normal(0, 1.8, n)
    )

    wind_speed = np.clip(
        12
        + 8 * np.sin(2 * np.pi * day_of_year / 17)
        + rng.normal(0, 5, n),
        0,
        45
    )

    # --------------------------------------------------------
    # Solar generation
    # Synthetic representation of Antarctic seasonal light
    # --------------------------------------------------------

    seasonal_light = np.clip(
        np.sin(2 * np.pi * (day_of_year - 80) / 365.25),
        0,
        1
    )

    daylight = np.clip(
        np.sin(np.pi * (hour - 5) / 14),
        0,
        1
    )

    solar_generation = (
        config["solar_capacity"]
        * seasonal_light
        * daylight
        * (0.85 + 0.15 * rng.random(n))
    )

    # Weather reduces solar efficiency
    cloud_factor = np.clip(
        1.0 - 0.012 * wind_speed + rng.normal(0, 0.04, n),
        0.55,
        1.0
    )

    solar_generation *= cloud_factor

    # --------------------------------------------------------
    # Occupancy
    # --------------------------------------------------------

    occupancy = np.clip(
        config["base_occupancy"]
        + 4 * np.sin(2 * np.pi * hour / 24)
        + rng.normal(0, 2, n),
        10,
        60
    ).round().astype(int)

    # --------------------------------------------------------
    # Building / station energy consumption
    #
    # Colder temperatures -> higher heating demand
    # Higher occupancy -> higher operational demand
    # --------------------------------------------------------

    heating_demand = np.maximum(
        0,
        (-temperature - 5) * 4.2
    )

    occupancy_demand = occupancy * 1.7

    base_load = (
        95
        + 12 * np.sin(2 * np.pi * hour / 24)
        + heating_demand
        + occupancy_demand
    )

    energy_consumption = np.clip(
        base_load + rng.normal(0, 8, n),
        50,
        None
    )

    # --------------------------------------------------------
    # Generator output
    #
    # Generator covers the deficit when solar is insufficient.
    # --------------------------------------------------------

    energy_deficit = np.maximum(
        0,
        energy_consumption - solar_generation
    )

    generator_output = np.clip(
        energy_deficit * 1.12
        + rng.normal(0, 4, n),
        0,
        config["generator_capacity"]
    )

    # --------------------------------------------------------
    # Battery simulation
    # --------------------------------------------------------

    battery = np.zeros(n)
    battery[0] = config["battery_capacity"] * 0.72

    for i in range(1, n):

        solar_surplus = max(
            0,
            solar_generation[i] - energy_consumption[i]
        )

        energy_deficit_now = max(
            0,
            energy_consumption[i] - solar_generation[i]
        )

        charge = solar_surplus * 0.82
        discharge = max(
            0,
            energy_deficit_now - generator_output[i]
        ) * 0.90

        battery[i] = np.clip(
            battery[i - 1] + charge - discharge,
            0,
            config["battery_capacity"]
        )

    battery_level_percent = (
        battery / config["battery_capacity"] * 100
    )

    # --------------------------------------------------------
    # Fuel consumption
    # --------------------------------------------------------

    generator_runtime_factor = generator_output / config["generator_capacity"]

    fuel_consumption = (
        2.0
        + generator_runtime_factor * 28
        + rng.normal(0, 0.8, n)
    )

    fuel_consumption = np.clip(
        fuel_consumption,
        0.5,
        None
    )

    fuel_level = np.zeros(n)
    fuel_level[0] = config["fuel_capacity"]

    for i in range(1, n):
        fuel_level[i] = max(
            0,
            fuel_level[i - 1] - fuel_consumption[i]
        )

    # --------------------------------------------------------
    # Water usage
    # --------------------------------------------------------

    water_consumption = np.clip(
        occupancy * 0.9
        + rng.normal(0, 1.5, n),
        5,
        None
    )

    water_level = np.zeros(n)
    water_level[0] = config["water_capacity"]

    for i in range(1, n):
        water_level[i] = max(
            0,
            water_level[i - 1] - water_consumption[i]
        )

    # --------------------------------------------------------
    # Food usage
    # --------------------------------------------------------

    food_consumption = np.clip(
        occupancy * 0.16
        + rng.normal(0, 0.25, n),
        1,
        None
    )

    food_stock = np.zeros(n)
    food_stock[0] = config["food_capacity"]

    for i in range(1, n):
        food_stock[i] = max(
            0,
            food_stock[i - 1] - food_consumption[i]
        )

    # --------------------------------------------------------
    # Building operational indicator
    # --------------------------------------------------------

    building_load = np.clip(
        energy_consumption * (
            0.88 + rng.normal(0, 0.03, n)
        ),
        30,
        None
    )

    # --------------------------------------------------------
    # Create DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame({
        "timestamp": timestamps,
        "station_id": station_name,
        "building_id": f"{station_name}_MAIN",
        "temperature_c": temperature.round(2),
        "wind_speed_kmh": wind_speed.round(2),
        "solar_generation_kw": solar_generation.round(2),
        "generator_output_kw": generator_output.round(2),
        "energy_consumption_kwh": energy_consumption.round(2),
        "battery_level_percent": battery_level_percent.round(2),
        "fuel_level_liters": fuel_level.round(2),
        "fuel_consumption_liters": fuel_consumption.round(2),
        "water_level_liters": water_level.round(2),
        "water_consumption_liters": water_consumption.round(2),
        "food_stock_kg": food_stock.round(2),
        "food_consumption_kg": food_consumption.round(2),
        "occupancy": occupancy,
        "building_load_kw": building_load.round(2),
    })

    return df


# ------------------------------------------------------------
# Generate Bharati + Maitri
# ------------------------------------------------------------

all_data = []

for station_name, config in stations.items():
    station_df = generate_station_data(
        station_name,
        config
    )

    all_data.append(station_df)


dataset = pd.concat(
    all_data,
    ignore_index=True
)

dataset = dataset.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

dataset.to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

print("=" * 70)
print("POLAR — SYNTHETIC ANTARCTIC DATASET")
print("=" * 70)

print(f"Output file : {OUTPUT_FILE}")
print(f"Rows        : {len(dataset)}")
print(f"Columns     : {len(dataset.columns)}")
print()

print("Stations:")
print(dataset["station_id"].value_counts())

print()
print("Date range:")
print(dataset["timestamp"].min())
print(dataset["timestamp"].max())

print()
print("Columns:")
for column in dataset.columns:
    print(f" - {column}")

print()
print("First 5 records:")
print(dataset.head().to_string(index=False))

print()
print("Missing values:")
print(dataset.isna().sum())

print()
print("Dataset generation completed successfully.")