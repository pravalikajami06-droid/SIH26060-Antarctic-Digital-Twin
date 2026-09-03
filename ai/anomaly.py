import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest


BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# LOAD NCPOR WEATHER DATA
# ---------------------------------------------------------

def load_weather_data(station: str) -> pd.DataFrame:

    if station.lower() == "bharati":

        file_path = (
            BASE_DIR
            / "data"
            / "raw"
            / "Bharati - AWS_2026_filtered_data.xlsx"
        )

    elif station.lower() == "maitri":

        file_path = (
            BASE_DIR
            / "data"
            / "raw"
            / "Maitri - AWS_2016_filtered_data.xlsx"
        )

    else:
        raise ValueError(
            "Station must be Bharati or Maitri"
        )

    df = pd.read_excel(file_path)

    df["obstime"] = pd.to_datetime(
        df["obstime"]
    )

    df = df.sort_values(
        "obstime"
    ).reset_index(drop=True)

    return df


# ---------------------------------------------------------
# ANOMALY DETECTION
# ---------------------------------------------------------

def detect_anomalies(
    station: str,
    sample_size: int = 5000
):

    df = load_weather_data(station)

    # Keep only required weather fields
    data = df[
        [
            "obstime",
            "tempr",
            "ap",
            "ws",
            "wd",
            "rh"
        ]
    ].copy()

    # -----------------------------------------------------
    # DATA QUALITY CLEANING
    # -----------------------------------------------------

    # NCPOR uses -999 as an invalid/missing-value marker.
    invalid_mask = (
        data[
            [
                "tempr",
                "ap",
                "ws",
                "wd",
                "rh"
            ]
        ] == -999
    ).any(axis=1)

    invalid_records = int(
        invalid_mask.sum()
    )

    # Replace invalid marker with NaN
    data = data.replace(
        -999,
        pd.NA
    )

    # Remove rows containing missing values
    data = data.dropna().copy()

    # Make sure numeric columns are numeric
    numeric_columns = [
        "tempr",
        "ap",
        "ws",
        "wd",
        "rh"
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data = data.dropna().copy()

    # Use only the most recent valid observations
    data = data.tail(
        sample_size
    ).reset_index(drop=True)

    if len(data) < 100:

        raise ValueError(
            "Not enough valid weather observations "
            "for anomaly detection."
        )

    # -----------------------------------------------------
    # FEATURES FOR ISOLATION FOREST
    # -----------------------------------------------------

    features = data[
        [
            "tempr",
            "ap",
            "ws",
            "rh"
        ]
    ]

    # -----------------------------------------------------
    # ISOLATION FOREST
    # -----------------------------------------------------

    model = IsolationForest(
        n_estimators=200,
        contamination=0.02,
        random_state=42,
        n_jobs=-1
    )

    predictions = model.fit_predict(
        features
    )

    scores = model.decision_function(
        features
    )

    data["anomaly"] = predictions
    data["anomaly_score"] = scores

    # -----------------------------------------------------
    # EXTRACT ANOMALIES
    # -----------------------------------------------------

    anomalies = data[
        data["anomaly"] == -1
    ].copy()

    anomalies = anomalies.sort_values(
        "anomaly_score"
    )

    results = []

    for _, row in anomalies.head(20).iterrows():

        results.append(
            {
                "timestamp": row[
                    "obstime"
                ].isoformat(),

                "temperature_c": round(
                    float(row["tempr"]),
                    2
                ),

                "air_pressure_hpa": round(
                    float(row["ap"]),
                    2
                ),

                "wind_speed": round(
                    float(row["ws"]),
                    2
                ),

                "wind_direction": round(
                    float(row["wd"]),
                    2
                ),

                "relative_humidity": round(
                    float(row["rh"]),
                    2
                ),

                "anomaly_score": round(
                    float(row["anomaly_score"]),
                    4
                )
            }
        )

    # -----------------------------------------------------
    # RETURN RESULTS
    # -----------------------------------------------------

    return {
        "station": station,

        "records_analyzed": len(data),

        "invalid_records_filtered": invalid_records,

        "anomalies_detected": len(anomalies),

        "anomalies": results
    }


# ---------------------------------------------------------
# DIRECT TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    for station in [
        "Bharati",
        "Maitri"
    ]:

        print(
            "\n" + "=" * 60
        )

        print(
            f"{station.upper()} ANOMALY DETECTION"
        )

        print(
            "=" * 60
        )

        result = detect_anomalies(
            station
        )

        print(
            f"Records analyzed: "
            f"{result['records_analyzed']}"
        )

        print(
            f"Invalid records filtered: "
            f"{result['invalid_records_filtered']}"
        )

        print(
            f"Anomalies detected: "
            f"{result['anomalies_detected']}"
        )

        print(
            "\nTop anomalies:"
        )

        for anomaly in result[
            "anomalies"
        ][:10]:

            print(anomaly)