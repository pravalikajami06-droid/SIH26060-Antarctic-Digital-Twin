// =========================================================
// POLAR — API CONNECTION
// Frontend ↔ FastAPI Backend
// =========================================================

const API_BASE_URL = "http://127.0.0.1:8000";

// ---------------------------------------------------------
// Generic API request
// ---------------------------------------------------------

async function apiRequest(endpoint) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        return await response.json();

    } catch (error) {
        console.error("POLAR API connection failed:", error);
        throw error;
    }
}

// ---------------------------------------------------------
// Backend health
// ---------------------------------------------------------

async function getHealth() {
    return await apiRequest("/health");
}

// ---------------------------------------------------------
// Weather
// ---------------------------------------------------------

async function getWeather(station, limit = 20) {
    return await apiRequest(
        `/weather/${station}?limit=${limit}`
    );
}

// ---------------------------------------------------------
// Weather summary
// ---------------------------------------------------------

async function getWeatherSummary(station) {
    return await apiRequest(
        `/weather/${station}/summary`
    );
}

// ---------------------------------------------------------
// AI anomaly detection
// ---------------------------------------------------------

async function getAnomalyDetection(station) {
    return await apiRequest(
        `/ai/anomaly/${station}`
    );
}

// ---------------------------------------------------------
// AI temperature forecast
// ---------------------------------------------------------

async function getTemperatureForecast(station, points = 24) {
    return await apiRequest(
        `/ai/forecast/${station}?forecast_points=${points}`
    );
}

// ---------------------------------------------------------
// AI insights
// ---------------------------------------------------------

async function getAIInsights(station) {
    return await apiRequest(
        `/ai/insights/${station}`
    );
}

// ---------------------------------------------------------
// Test backend connection
// ---------------------------------------------------------

async function testBackendConnection() {
    try {

        const result = await getHealth();

        console.log("POLAR Backend Connected:", result);

        return true;

    } catch (error) {

        console.error("POLAR Backend unavailable");

        return false;
    }
}