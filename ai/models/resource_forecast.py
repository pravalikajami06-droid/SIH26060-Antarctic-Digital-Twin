import json
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# POLAR — RESOURCE FORECASTING
# SIH26060 — Antarctic Digital Twin
#
# Predicts remaining resource duration for:
# Fuel, Water and Food.
#
# Uses recent consumption trends from operational data.
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

OUTPUT_FILE = OUTPUT_DIR / "resource_forecast.json"


print("=" * 70)
print("POLAR — RESOURCE FORECASTING")
print("=" * 70)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values(
    ["station_id", "timestamp"]
).reset_index(drop=True)

print(f"Input rows    : {len(df)}")
print(f"Input columns : {len(df.columns)}")


# ------------------------------------------------------------
# Helper function
# ------------------------------------------------------------

def safe_positive(value):
    """Return a positive finite value or zero."""

    value = float(value)

    if not np.isfinite(value):
        return 0.0

    return max(value, 0.0)


def calculate_days_remaining(
    current_stock,
    consumption_rate_per_day
):
    """
    Estimate number of days remaining.

    Formula:
        days = current stock / daily consumption
    """

    current_stock = safe_positive(current_stock)
    consumption_rate_per_day = safe_positive(
        consumption_rate_per_day
    )

    if consumption_rate_per_day <= 0:
        return None

    return current_stock / consumption_rate_per_day


def resource_level(days_remaining):
    """Convert remaining days into operational risk."""

    if days_remaining is None:
        return "UNKNOWN"

    if days_remaining <= 3:
        return "CRITICAL"

    if days_remaining <= 7:
        return "HIGH"

    if days_remaining <= 14:
        return "MEDIUM"

    return "LOW"


# ------------------------------------------------------------
# Analyze one station
# ------------------------------------------------------------

def analyze_station(station_name, station_df):

    station_df = station_df.copy()

    station_df = station_df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Use the latest operational reading
    # --------------------------------------------------------

    latest = station_df.iloc[-1]

    latest_timestamp = latest["timestamp"]

    # --------------------------------------------------------
    # Estimate daily consumption
    #
    # Dataset is hourly, therefore:
    # hourly mean × 24 = daily consumption
    #
    # We use the last 7 days where possible to capture
    # recent operational behavior.
    # --------------------------------------------------------

    recent_hours = min(
        len(station_df),
        24 * 7
    )

    recent = station_df.tail(
        recent_hours
    )

    fuel_daily = (
        recent["fuel_consumption_liters"]
        .mean()
        * 24
    )

    water_daily = (
        recent["water_consumption_liters"]
        .mean()
        * 24
    )

    food_daily = (
        recent["food_consumption_kg"]
        .mean()
        * 24
    )

    # --------------------------------------------------------
    # Current resource levels
    # --------------------------------------------------------

    current_fuel = safe_positive(
        latest["fuel_level_liters"]
    )

    current_water = safe_positive(
        latest["water_level_liters"]
    )

    current_food = safe_positive(
        latest["food_stock_kg"]
    )

    current_battery = safe_positive(
        latest["battery_level_percent"]
    )

    # --------------------------------------------------------
    # Calculate remaining days
    # --------------------------------------------------------

    fuel_days = calculate_days_remaining(
        current_fuel,
        fuel_daily
    )

    water_days = calculate_days_remaining(
        current_water,
        water_daily
    )

    food_days = calculate_days_remaining(
        current_food,
        food_daily
    )

    # --------------------------------------------------------
    # Resource risk levels
    # --------------------------------------------------------

    fuel_risk = resource_level(
        fuel_days
    )

    water_risk = resource_level(
        water_days
    )

    food_risk = resource_level(
        food_days
    )

    # --------------------------------------------------------
    # Battery risk
    # --------------------------------------------------------

    if current_battery <= 20:
        battery_risk = "CRITICAL"
    elif current_battery <= 40:
        battery_risk = "HIGH"
    elif current_battery <= 60:
        battery_risk = "MEDIUM"
    else:
        battery_risk = "LOW"

    # --------------------------------------------------------
    # Find minimum resource duration
    # --------------------------------------------------------

    valid_days = [
        value
        for value in [
            fuel_days,
            water_days,
            food_days
        ]
        if value is not None
    ]

    if valid_days:
        minimum_days = min(valid_days)
    else:
        minimum_days = None

    # --------------------------------------------------------
    # Identify limiting resource
    # --------------------------------------------------------

    resource_days = {
        "fuel": fuel_days,
        "water": water_days,
        "food": food_days
    }

    valid_resources = {
        key: value
        for key, value in resource_days.items()
        if value is not None
    }

    if valid_resources:
        limiting_resource = min(
            valid_resources,
            key=valid_resources.get
        )
    else:
        limiting_resource = "unknown"

    # --------------------------------------------------------
    # Overall resource risk
    # --------------------------------------------------------

    risk_levels = [
        fuel_risk,
        water_risk,
        food_risk,
        battery_risk
    ]

    if "CRITICAL" in risk_levels:
        overall_risk = "CRITICAL"

    elif "HIGH" in risk_levels:
        overall_risk = "HIGH"

    elif "MEDIUM" in risk_levels:
        overall_risk = "MEDIUM"

    else:
        overall_risk = "LOW"

    # --------------------------------------------------------
    # Generate recommendation
    # --------------------------------------------------------

    recommendations = []

    if fuel_risk in ["CRITICAL", "HIGH"]:
        recommendations.append(
            "Prioritize fuel resupply and reduce generator dependency"
        )

    if water_risk in ["CRITICAL", "HIGH"]:
        recommendations.append(
            "Prioritize water conservation and resupply"
        )

    if food_risk in ["CRITICAL", "HIGH"]:
        recommendations.append(
            "Prioritize food resupply and review consumption"
        )

    if battery_risk in ["CRITICAL", "HIGH"]:
        recommendations.append(
            "Reduce non-essential electrical loads and protect battery reserve"
        )

    if not recommendations:
        recommendations.append(
            "Resource levels are currently within acceptable operating range"
        )

    # --------------------------------------------------------
    # Prepare result
    # --------------------------------------------------------

    result = {
        "station_id": station_name,
        "timestamp": str(latest_timestamp),

        "current_resources": {
            "fuel_level_liters": round(
                current_fuel,
                2
            ),
            "water_level_liters": round(
                current_water,
                2
            ),
            "food_stock_kg": round(
                current_food,
                2
            ),
            "battery_level_percent": round(
                current_battery,
                2
            )
        },

        "daily_consumption": {
            "fuel_liters_per_day": round(
                fuel_daily,
                2
            ),
            "water_liters_per_day": round(
                water_daily,
                2
            ),
            "food_kg_per_day": round(
                food_daily,
                2
            )
        },

        "estimated_days_remaining": {
            "fuel": (
                round(fuel_days, 2)
                if fuel_days is not None
                else None
            ),
            "water": (
                round(water_days, 2)
                if water_days is not None
                else None
            ),
            "food": (
                round(food_days, 2)
                if food_days is not None
                else None
            )
        },

        "resource_risk": {
            "fuel": fuel_risk,
            "water": water_risk,
            "food": food_risk,
            "battery": battery_risk,
            "overall": overall_risk
        },

        "limiting_resource": limiting_resource,

        "minimum_resource_days": (
            round(minimum_days, 2)
            if minimum_days is not None
            else None
        ),

        "recommendations": recommendations
    }

    return result


# ------------------------------------------------------------
# Process all stations
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
        f"Fuel remaining days  : "
        f"{result['estimated_days_remaining']['fuel']}"
    )

    print(
        f"Water remaining days : "
        f"{result['estimated_days_remaining']['water']}"
    )

    print(
        f"Food remaining days  : "
        f"{result['estimated_days_remaining']['food']}"
    )

    print(
        f"Limiting resource    : "
        f"{result['limiting_resource']}"
    )

    print(
        f"Overall resource risk: "
        f"{result['resource_risk']['overall']}"
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
print("RESOURCE FORECASTING COMPLETED SUCCESSFULLY")
print("=" * 70)

print()
print("Output file:")
print(OUTPUT_FILE)

print()
print("Stations processed:")

for station_name in results:

    print(
        f" - {station_name}: "
        f"{results[station_name]['resource_risk']['overall']} "
        f"resource risk"
    )