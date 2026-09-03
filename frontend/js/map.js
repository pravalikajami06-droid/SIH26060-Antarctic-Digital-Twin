// =========================================================
// POLAR — ANTARCTIC STATION MAP
// =========================================================

document.addEventListener("DOMContentLoaded", () => {

    const mapElement = document.getElementById("antarctic-map");

    if (!mapElement) {
        return;
    }

    // Create Antarctic map
    const map = L.map("antarctic-map", {
        center: [-75, 0],
        zoom: 3,
        minZoom: 2,
        maxZoom: 7,
        zoomControl: true
    });

    // Light map tiles
    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution: "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);


    // =====================================================
    // ANTARCTIC RESEARCH STATIONS
    // =====================================================

    const stations = [
        {
            name: "McMurdo Station",
            lat: -77.8419,
            lon: 166.6863,
            temperature: -18.4,
            status: "Operational"
        },
        {
            name: "Amundsen-Scott South Pole",
            lat: -90,
            lon: 0,
            temperature: -51.2,
            status: "Operational"
        },
        {
            name: "Concordia Station",
            lat: -75.1000,
            lon: 123.3300,
            temperature: -42.7,
            status: "Operational"
        },
        {
            name: "Vostok Station",
            lat: -78.4640,
            lon: 106.8370,
            temperature: -55.8,
            status: "Operational"
        },
        {
            name: "Halley VI",
            lat: -75.6050,
            lon: -26.2090,
            temperature: -21.5,
            status: "Operational"
        },
        {
            name: "Mawson Station",
            lat: -67.6027,
            lon: 62.8738,
            temperature: -12.8,
            status: "Operational"
        }
    ];


    // =====================================================
    // CUSTOM STATION ICON
    // =====================================================

    const stationIcon = L.divIcon({
        className: "polar-station-marker",

        html: `
            <div style="
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #159ac0;
                border: 3px solid white;
                box-shadow: 0 1px 8px rgba(21,154,192,0.5);
            "></div>
        `,

        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });


    // =====================================================
    // ADD STATIONS
    // =====================================================

    stations.forEach(station => {

        const marker = L.marker(
            [station.lat, station.lon],
            {
                icon: stationIcon
            }
        ).addTo(map);


        marker.bindPopup(`
            <div style="
                min-width: 170px;
                font-family: Arial, sans-serif;
            ">

                <strong style="
                    font-size: 14px;
                    color: #173042;
                ">
                    ${station.name}
                </strong>

                <br><br>

                <span style="color:#607987;">
                    Temperature
                </span>

                <strong>
                    ${station.temperature} °C
                </strong>

                <br>

                <span style="color:#607987;">
                    Status
                </span>

                <strong style="color:#15966b;">
                    ${station.status}
                </strong>

            </div>
        `);
    });


    // =====================================================
    // EXPOSE MAP
    // =====================================================

    window.polarMap = map;
    window.polarStations = stations;

});