import json
from pathlib import Path

import pandas as pd


# ============================================================
# POLAR — RISK / DECISION ENGINE
# SIH26060 — Antarctic Digital Twin
#
# Combines:
#   1. Energy forecast
#   2. Anomaly detection
#   3. Resource forecast
#   4. Environmental conditions
#
# Produces explainable operational risk and recommendations.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "engineered_operational_data.csv"
)

ENERGY_FILE = (
    BASE_DIR
    / "outputs"
    / "energy_forecast.json"
)

ANOMALY_FILE = (
    BASE_DIR
    / "outputs"
    / "anomaly_detection.json"
)

RESOURCE_FILE = (
    BASE_DIR
    / "outputs"
    / "resource_forecast.json"
)

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "risk_assessment.json"


print("=" * 75)
print("POLAR — RISK / DECISION ENGINE")
print("=" * 75)


# ------------------------------------------------------------
# Load files
# ------------------------------------------------------------

df = pd.read_csv(DATA_FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)

with open(
    ENERGY_FILE,
    "r",
    encoding="utf-8"
) as file:
    energy_data = json.load(file)

with open(
    ANOMALY_FILE,
    "r",
    encoding="utf-8"
) as file:
    anomaly_data = json.load(file)

with open(
    RESOURCE_FILE,
    "r",
    encoding="utf-8"
) as file:
    resource_data = json.load(file)


print(f"Input rows : {len(df)}")
print()


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def clamp(value, minimum=0, maximum=100):
    return max(
        minimum,
        min(maximum, float(value))
    )


def risk_level(score):

    if score >= 75:
        return "CRITICAL"

    if score >= 50:
        return "HIGH"

    if score >= 25:
        return "MEDIUM"

    return "LOW"


# ------------------------------------------------------------
# Process each station
# ------------------------------------------------------------

results = {}


for station in sorted(
    df["station_id"].unique()
):

    print(
        f"Processing station: {station}"
    )

    station_df = df[
        df["station_id"] == station
    ].sort_values(
        "timestamp"
    )

    latest = station_df.iloc[-1]


    # ========================================================
    # 1. ENVIRONMENTAL RISK
    # ========================================================

    temperature = float(
        latest["temperature_c"]
    )

    wind_speed = float(
        latest["wind_speed_kmh"]
    )

    environmental_score = 0

    environmental_reasons = []


    # Extreme cold
    if temperature <= -25:

        environmental_score += 30

        environmental_reasons.append(
            "Extreme cold may increase heating demand"
        )

    elif temperature <= -15:

        environmental_score += 15

        environmental_reasons.append(
            "Low temperature may increase energy demand"
        )


    # Strong wind
    if wind_speed >= 60:

        environmental_score += 30

        environmental_reasons.append(
            "Strong winds may affect outdoor operations"
        )

    elif wind_speed >= 40:

        environmental_score += 15

        environmental_reasons.append(
            "Elevated wind conditions"
        )


    environmental_score = clamp(
        environmental_score
    )


    # ========================================================
    # 2. ENERGY RISK
    # ========================================================

    energy_info = energy_data.get(
        station,
        {}
    )

    energy_forecast = energy_info.get(
        "forecast",
        []
    )

    if energy_forecast:

        forecast_values = []

        for item in energy_forecast:

            if isinstance(item, dict):

                value = item.get(
                    "predicted_energy_kwh"
                )

                if value is not None:
                    forecast_values.append(
                        float(value)
                    )

            else:

                try:
                    forecast_values.append(
                        float(item)
                    )
                except (TypeError, ValueError):
                    pass

        if forecast_values:

            average_energy_forecast = (
                sum(forecast_values)
                / len(forecast_values)
            )

        else:

            average_energy_forecast = float(
                latest["energy_consumption_kwh"]
            )

    else:

        average_energy_forecast = float(
            latest["energy_consumption_kwh"]
        )


    current_energy = float(
        latest["energy_consumption_kwh"]
    )


    energy_change_percent = 0

    if current_energy > 0:

        energy_change_percent = (
            (
                average_energy_forecast
                - current_energy
            )
            / current_energy
        ) * 100


    energy_score = 0

    energy_reasons = []


    if energy_change_percent >= 20:

        energy_score += 35

        energy_reasons.append(
            "Forecast indicates significantly higher energy demand"
        )

    elif energy_change_percent >= 10:

        energy_score += 20

        energy_reasons.append(
            "Forecast indicates increased energy demand"
        )


    generator_dependency = float(
        latest.get(
            "generator_dependency_percent",
            0
        )
    )


    if generator_dependency >= 80:

        energy_score += 35

        energy_reasons.append(
            "High dependency on generator power"
        )

    elif generator_dependency >= 60:

        energy_score += 20

        energy_reasons.append(
            "Elevated generator dependency"
        )


    energy_score = clamp(
        energy_score
    )


    # ========================================================
    # 3. ANOMALY RISK
    # ========================================================

    anomaly_info = anomaly_data.get(
        station,
        {}
    )

    average_anomaly_score = float(
        anomaly_info.get(
            "average_score",
            0
        )
    )

    highest_anomaly_score = float(
        anomaly_info.get(
            "highest_score",
            0
        )
    )

    anomaly_records = int(
        anomaly_info.get(
            "anomaly_records",
            0
        )
    )

    warning_records = int(
        anomaly_info.get(
            "warning_records",
            0
        )
    )


    anomaly_score = clamp(
        average_anomaly_score * 100
    )

    anomaly_reasons = []


    if anomaly_records > 0:

        anomaly_score = max(
            anomaly_score,
            70
        )

        anomaly_reasons.append(
            f"{anomaly_records} anomaly records detected"
        )

    elif warning_records > 0:

        anomaly_reasons.append(
            f"{warning_records} warning records detected"
        )


    if highest_anomaly_score >= 0.7:

        anomaly_score = max(
            anomaly_score,
            60
        )

        anomaly_reasons.append(
            "High anomaly score observed"
        )


    anomaly_score = clamp(
        anomaly_score
    )


    # ========================================================
    # 4. RESOURCE RISK
    # ========================================================

    resource_info = resource_data.get(
        station,
        {}
    )

    resource_risk = resource_info.get(
        "resource_risk",
        {}
    )

    fuel_days = resource_info.get(
        "estimated_days_remaining",
        {}
    ).get(
        "fuel"
    )

    water_days = resource_info.get(
        "estimated_days_remaining",
        {}
    ).get(
        "water"
    )

    food_days = resource_info.get(
        "estimated_days_remaining",
        {}
    ).get(
        "food"
    )

    limiting_resource = resource_info.get(
        "limiting_resource",
        "unknown"
    )


    resource_score = 0

    resource_reasons = []


    overall_resource_risk = resource_risk.get(
        "overall",
        "UNKNOWN"
    )


    if overall_resource_risk == "CRITICAL":

        resource_score = 90

        resource_reasons.append(
            "Critical resource shortage predicted"
        )

    elif overall_resource_risk == "HIGH":

        resource_score = 70

        resource_reasons.append(
            "High resource shortage risk"
        )

    elif overall_resource_risk == "MEDIUM":

        resource_score = 45

        resource_reasons.append(
            "Medium resource consumption risk"
        )

    elif overall_resource_risk == "LOW":

        resource_score = 15


    if limiting_resource != "unknown":

        resource_reasons.append(
            f"Limiting resource: {limiting_resource}"
        )


    resource_score = clamp(
        resource_score
    )


    # ========================================================
    # 5. COMBINED RISK SCORE
    # ========================================================

    overall_score = (
        environmental_score * 0.20
        + energy_score * 0.30
        + anomaly_score * 0.20
        + resource_score * 0.30
    )

    overall_score = round(
        clamp(overall_score),
        2
    )


    overall_level = risk_level(
        overall_score
    )


    # ========================================================
    # 6. DECISION / RECOMMENDATIONS
    # ========================================================

    recommendations = []


    if overall_level == "CRITICAL":

        recommendations.append(
            "Initiate immediate operational review"
        )


    if energy_score >= 50:

        recommendations.append(
            "Reduce non-essential electrical loads"
        )


    if resource_score >= 50:

        recommendations.append(
            f"Prioritize {limiting_resource} resource management"
        )


    if environmental_score >= 50:

        recommendations.append(
            "Prepare for severe environmental operating conditions"
        )


    if anomaly_score >= 50:

        recommendations.append(
            "Inspect systems associated with abnormal operating behavior"
        )


    if not recommendations:

        recommendations.append(
            "Continue normal monitoring and operational planning"
        )


    # Remove duplicate recommendations
    recommendations = list(
        dict.fromkeys(
            recommendations
        )
    )


    # ========================================================
    # 7. EXPLAINABILITY
    # ========================================================

    reasons = (
        environmental_reasons
        + energy_reasons
        + anomaly_reasons
        + resource_reasons
    )


    if not reasons:

        reasons.append(
            "No significant risk drivers detected"
        )


    # ========================================================
    # 8. FINAL RESULT
    # ========================================================

    results[station] = {

        "station_id": station,

        "timestamp": str(
            latest["timestamp"]
        ),

        "risk_score": overall_score,

        "risk_level": overall_level,

        "risk_components": {

            "environmental_risk": round(
                environmental_score,
                2
            ),

            "energy_risk": round(
                energy_score,
                2
            ),

            "anomaly_risk": round(
                anomaly_score,
                2
            ),

            "resource_risk": round(
                resource_score,
                2
            )
        },

        "environment": {

            "temperature_c": round(
                temperature,
                2
            ),

            "wind_speed_kmh": round(
                wind_speed,
                2
            )
        },

        "energy": {

            "current_energy_kwh": round(
                current_energy,
                2
            ),

            "average_forecast_kwh": round(
                average_energy_forecast,
                2
            ),

            "forecast_change_percent": round(
                energy_change_percent,
                2
            )
        },

        "resources": {

            "fuel_days_remaining": fuel_days,

            "water_days_remaining": water_days,

            "food_days_remaining": food_days,

            "limiting_resource": limiting_resource
        },

        "anomaly": {

            "average_score": round(
                average_anomaly_score,
                4
            ),

            "highest_score": round(
                highest_anomaly_score,
                4
            ),

            "warning_records": warning_records,

            "anomaly_records": anomaly_records
        },

        "decision": {

            "recommendations": recommendations,

            "risk_drivers": reasons
        }
    }


    print(
        f"Risk score : {overall_score}"
    )

    print(
        f"Risk level : {overall_level}"
    )

    print(
        f"Limiting resource : {limiting_resource}"
    )


# ------------------------------------------------------------
# Save result
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
# Completion
# ------------------------------------------------------------

print()
print("=" * 75)
print("RISK / DECISION ENGINE COMPLETED SUCCESSFULLY")
print("=" * 75)

print()
print("Output file:")
print(OUTPUT_FILE)

print()
print("Stations processed:")

for station in results:

    print(
        f"- {station}: "
        f"{results[station]['risk_level']} "
        f"risk "
        f"({results[station]['risk_score']})"
    )