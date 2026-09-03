// =========================================================
// POLAR — APPLICATION CONTROLLER
// =========================================================

document.addEventListener("DOMContentLoaded", async () => {

    console.log("POLAR frontend initialized.");

    // Test backend connection
    const connected = await testBackendConnection();

    if (connected) {

        console.log("✓ FastAPI backend connected");

        updateBackendStatus(true);

    } else {

        console.warn("✕ FastAPI backend unavailable");

        updateBackendStatus(false);
    }

});


// =========================================================
// BACKEND STATUS UI
// =========================================================

function updateBackendStatus(connected) {

    const statusElement =
        document.getElementById("backend-status");

    if (!statusElement) return;

    if (connected) {

        statusElement.textContent = "LIVE DATA";
        statusElement.classList.add("connected");

    } else {

        statusElement.textContent = "OFFLINE";
        statusElement.classList.remove("connected");
    }
}