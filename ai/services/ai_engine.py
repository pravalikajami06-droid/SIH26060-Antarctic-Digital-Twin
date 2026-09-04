import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"

ENERGY_FILE = OUTPUT_DIR / "energy_forecast.json"
ANOMALY_FILE = OUTPUT_DIR / "anomaly_detection.json"
RESOURCE_FILE = OUTPUT_DIR / "resource_forecast.json"
RISK_FILE = OUTPUT_DIR / "risk_assessment.json"

FINAL_FILE = OUTPUT_DIR / "ai_insights.json"


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def station_name(item):
    return (
        item.get("station_id")
        or item.get("station")
        or item.get("station_name")
    )


def normalize_station_data(data):
    """
    Convert different possible JSON structures into:
    {
        "Bharati": {...},
        "Maitri": {...}
    }
    """

    result = {}

    if isinstance(data, dict):

        # Case 1:
        # {"Bharati": {...}, "Maitri": {...}}
        for key, value in data.items():
            if key.lower() in ["bharati", "maitri"]:
                result[key.capitalize()] = value

        if result:
            return result

        # Case 2:
        # {"stations": [...]}
        if isinstance(data.get("stations"), list):
            data = data["stations"]

        # Case 3:
        # {"results": [...]}
        elif isinstance(data.get("results"), list):
            data = data["results"]

        # Case 4:
        # {"data": [...]}
        elif isinstance(data.get("data"), list):
            data = data["data"]

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name = station_name(item)

                if name:
                    result[name.capitalize()] = item

    return result


def get_station(data, station):
    normalized = normalize_station_data(data)

    if station in normalized:
        return normalized[station]

    # Try case-insensitive matching
    for key, value in normalized.items():
        if key.lower() == station.lower():
            return value

    return {}


def first_value(data, keys, default=None):
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data:
            return data[key]

    return default


def create_station_output(
    station,
    energy,
    anomaly,
    resource,
    risk
):
    energy_data = get_station(energy, station)
    anomaly_data = get_station(anomaly, station)
    resource_data = get_station(resource, station)
    risk_data = get_station(risk, station)

    forecast = first_value(
        energy_data,
        [
            "forecast_24h",
            "24h_forecast",
            "forecast",
            "predicted_energy",
            "energy_prediction",
            "mean_forecast"
        ],
        []
    )

    if isinstance(forecast, (int, float)):
        energy_prediction = forecast
    elif isinstance(forecast, list) and forecast:
        numeric_values = [
            x for x in forecast
            if isinstance(x, (int, float))
        ]

        energy_prediction = (
            sum(numeric_values) / len(numeric_values)
            if numeric_values else None
        )
    else:
        energy_prediction = first_value(
            energy_data,
            ["mean_forecast", "predicted_energy", "energy_prediction"],
            None
        )

    anomaly_score = first_value(
        anomaly_data,
        [
            "highest_score",
            "max_score",
            "average_score",
            "anomaly_score"
        ],
        0
    )

    anomaly_count = first_value(
        anomaly_data,
        [
            "anomaly_records",
            "anomalies",
            "anomaly_count",
            "total_anomalies"
        ],
        0
    )

    warning_count = first_value(
        anomaly_data,
        [
            "warning_records",
            "warnings",
            "warning_count",
            "total_warnings"
        ],
        0
    )

    fuel_days = first_value(
        resource_data,
        [
            "fuel_remaining_days",
            "fuel_days"
        ],
        0
    )

    water_days = first_value(
        resource_data,
        [
            "water_remaining_days",
            "water_days"
        ],
        0
    )

    food_days = first_value(
        resource_data,
        [
            "food_remaining_days",
            "food_days"
        ],
        0
    )

    limiting_resource = first_value(
        resource_data,
        [
            "limiting_resource",
            "limiting"
        ],
        "fuel"
    )

    resource_risk = first_value(
        resource_data,
        [
            "overall_resource_risk",
            "resource_risk",
            "risk_level"
        ],
        "UNKNOWN"
    )

    risk_score = first_value(
        risk_data,
        [
            "risk_score",
            "score"
        ],
        0
    )

    risk_level = first_value(
        risk_data,
        [
            "risk_level",
            "level"
        ],
        "UNKNOWN"
    )

    recommendation = first_value(
        risk_data,
        [
            "recommendation",
            "recommended_action",
            "action"
        ],
        None
    )

    if recommendation is None:
        if str(risk_level).upper() == "HIGH":
            recommendation = "Prepare backup generator and monitor critical resources."
        elif str(risk_level).upper() == "MEDIUM":
            recommendation = "Monitor energy demand and resource levels."
        else:
            recommendation = "Continue normal station operations."

    return {
        "station_id": station,
        "energy_forecast": {
            "prediction_24h": energy_prediction
        },
        "anomaly_detection": {
            "anomaly_score": anomaly_score,
            "warning_count": warning_count,
            "anomaly_count": anomaly_count
        },
        "resource_forecast": {
            "fuel_remaining_days": fuel_days,
            "water_remaining_days": water_days,
            "food_remaining_days": food_days,
            "limiting_resource": limiting_resource,
            "resource_risk": resource_risk
        },
        "risk_assessment": {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "recommendation": recommendation
        }
    }


def main():

    print("=" * 70)
    print("POLAR - FINAL AI INTELLIGENCE OUTPUT")
    print("=" * 70)

    energy = load_json(ENERGY_FILE)
    anomaly = load_json(ANOMALY_FILE)
    resource = load_json(RESOURCE_FILE)
    risk = load_json(RISK_FILE)

    stations = ["Bharati", "Maitri"]

    final_output = {
        "project": "POLAR - Antarctic Digital Twin",
        "module": "AI + Data Intelligence",
        "data_type": "Synthetic operational data",
        "stations": {}
    }

    for station in stations:

        print()
        print(f"Processing station: {station}")

        station_output = create_station_output(
            station,
            energy,
            anomaly,
            resource,
            risk
        )

        final_output["stations"][station] = station_output

        print(
            f"Energy prediction : "
            f"{station_output['energy_forecast']['prediction_24h']}"
        )

        print(
            f"Anomaly score     : "
            f"{station_output['anomaly_detection']['anomaly_score']}"
        )

        print(
            f"Resource risk     : "
            f"{station_output['resource_forecast']['resource_risk']}"
        )

        print(
            f"Risk score        : "
            f"{station_output['risk_assessment']['risk_score']}"
        )

        print(
            f"Risk level        : "
            f"{station_output['risk_assessment']['risk_level']}"
        )

        print(
            f"Recommendation    : "
            f"{station_output['risk_assessment']['recommendation']}"
        )

    with open(FINAL_FILE, "w", encoding="utf-8") as file:
        json.dump(
            final_output,
            file,
            indent=4
        )

    print()
    print("=" * 70)
    print("FINAL AI JSON OUTPUT COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print()
    print(f"Output file:")
    print(FINAL_FILE)

    print()
    print("Stations processed:")
    print("- Bharati")
    print("- Maitri")


if __name__ == "__main__":
    main()