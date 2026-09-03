// ============================================================
// POLAR — ANTARCTIC 3D DIGITAL TWIN
// Plain JavaScript + Three.js
// ============================================================

let twinScene;
let twinCamera;
let twinRenderer;

let twinTerrain;
let twinTerrainWire;
let twinStations = [];
let twinGroup;

let isDragging = false;
let previousMouseX = 0;
let previousMouseY = 0;

let rotationX = 0;
let rotationY = 0;


// ============================================================
// INITIALIZE DIGITAL TWIN
// ============================================================

function initDigitalTwin() {

    const container = document.getElementById("digital-twin");

    if (!container || typeof THREE === "undefined") {
        console.warn("POLAR Digital Twin: Three.js not ready.");
        return;
    }

    container.innerHTML = "";

    // --------------------------------------------------------
    // SCENE
    // --------------------------------------------------------

    twinScene = new THREE.Scene();

    twinScene.background = new THREE.Color(0xf4fafc);


    // --------------------------------------------------------
    // CAMERA
    // --------------------------------------------------------

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 400;

    twinCamera = new THREE.PerspectiveCamera(
        38,
        width / height,
        0.1,
        100
    );

    twinCamera.position.set(0, 5.2, 7.5);

    twinCamera.lookAt(0, 0, 0);


    // --------------------------------------------------------
    // RENDERER
    // --------------------------------------------------------

    twinRenderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false
    });

    twinRenderer.setPixelRatio(
        Math.min(window.devicePixelRatio || 1, 2)
    );

    twinRenderer.setSize(width, height);

    twinRenderer.shadowMap.enabled = true;

    container.appendChild(twinRenderer.domElement);


    // --------------------------------------------------------
    // LIGHTING
    // --------------------------------------------------------

    const ambientLight = new THREE.AmbientLight(
        0xffffff,
        2.4
    );

    twinScene.add(ambientLight);


    const sunLight = new THREE.DirectionalLight(
        0xffffff,
        3.2
    );

    sunLight.position.set(5, 8, 6);

    sunLight.castShadow = true;

    twinScene.add(sunLight);


    const fillLight = new THREE.DirectionalLight(
        0xbfefff,
        1.2
    );

    fillLight.position.set(-5, 4, -4);

    twinScene.add(fillLight);


    // --------------------------------------------------------
    // MAIN GROUP
    // --------------------------------------------------------

    twinGroup = new THREE.Group();

    twinScene.add(twinGroup);


    // --------------------------------------------------------
    // ANTARCTIC TERRAIN
    // --------------------------------------------------------

    createAntarcticTerrain();


    // --------------------------------------------------------
    // TERRAIN GRID
    // --------------------------------------------------------

    createTerrainGrid();


    // --------------------------------------------------------
    // STATIONS
    // --------------------------------------------------------

    createStations();


    // --------------------------------------------------------
    // POLAR ICE RINGS
    // --------------------------------------------------------

    createIceRings();


    // --------------------------------------------------------
    // INTERACTION
    // --------------------------------------------------------

    setupInteraction(container);


    // --------------------------------------------------------
    // RESPONSIVE
    // --------------------------------------------------------

    window.addEventListener("resize", resizeDigitalTwin);


    // --------------------------------------------------------
    // START ANIMATION
    // --------------------------------------------------------

    animateDigitalTwin();
}


// ============================================================
// CREATE ANTARCTIC TERRAIN
// ============================================================

function createAntarcticTerrain() {

    const size = 6.2;
    const segments = 55;

    const geometry = new THREE.PlaneGeometry(
        size,
        size,
        segments,
        segments
    );

    const position = geometry.attributes.position;


    // --------------------------------------------------------
    // TERRAIN HEIGHT FUNCTION
    // --------------------------------------------------------

    for (let i = 0; i < position.count; i++) {

        const x = position.getX(i);
        const z = position.getY(i);

        const distance = Math.sqrt(
            x * x + z * z
        );

        // Antarctic boundary
        const radius = 3.0;

        // Natural terrain noise
        const largeTerrain =
            Math.sin(x * 2.0) *
            Math.cos(z * 1.8) *
            0.16;

        const mediumTerrain =
            Math.sin(x * 5.0 + z * 1.5) *
            Math.cos(z * 4.0) *
            0.055;

        const mountainTerrain =
            Math.sin(x * 1.4 - z * 1.2) *
            0.12;

        // Central elevation
        const elevation =
            0.20 +
            largeTerrain +
            mediumTerrain +
            mountainTerrain;


        // Fade terrain towards Antarctic boundary
        let boundaryFactor =
            1 - Math.max(
                0,
                (distance - radius + 0.4) / 0.8
            );

        boundaryFactor = Math.max(
            0,
            Math.min(1, boundaryFactor)
        );


        const finalHeight =
            elevation * boundaryFactor;


        position.setZ(i, finalHeight);
    }


    // Plane is initially XY.
    // Rotate so Z becomes vertical.
    geometry.rotateX(-Math.PI / 2);

    geometry.computeVertexNormals();


    // --------------------------------------------------------
    // TERRAIN MATERIAL
    // --------------------------------------------------------

    const material =
        new THREE.MeshStandardMaterial({

            color: 0xdceff4,

            roughness: 0.92,

            metalness: 0.02,

            side: THREE.DoubleSide
        });


    twinTerrain =
        new THREE.Mesh(
            geometry,
            material
        );


    twinTerrain.position.y = -0.05;

    twinTerrain.rotation.x = -0.12;

    twinGroup.add(twinTerrain);


    // --------------------------------------------------------
    // ICE CORE
    // --------------------------------------------------------

    const coreGeometry =
        new THREE.CylinderGeometry(
            2.75,
            2.95,
            0.18,
            64
        );


    const coreMaterial =
        new THREE.MeshStandardMaterial({

            color: 0xc7e9f1,

            roughness: 0.88,

            metalness: 0.01
        });


    const iceCore =
        new THREE.Mesh(
            coreGeometry,
            coreMaterial
        );


    iceCore.position.y = -0.18;

    twinGroup.add(iceCore);
}


// ============================================================
// TERRAIN GRID
// ============================================================

function createTerrainGrid() {

    const wireGeometry =
        new THREE.PlaneGeometry(
            6.18,
            6.18,
            25,
            25
        );


    const wireMaterial =
        new THREE.MeshBasicMaterial({

            color: 0x79cfe0,

            wireframe: true,

            transparent: true,

            opacity: 0.24
        });


    twinTerrainWire =
        new THREE.Mesh(
            wireGeometry,
            wireMaterial
        );


    twinTerrainWire.rotation.x =
        -Math.PI / 2;


    twinTerrainWire.position.y =
        0.025;


    twinTerrainWire.scale.set(
        0.96,
        0.96,
        0.96
    );


    twinGroup.add(twinTerrainWire);
}


// ============================================================
// RESEARCH STATIONS
// ============================================================

function createStations() {

    const stationData = [

        {
            name: "Halley VI",
            x: -1.45,
            z: 0.65,
            temperature: -21.5
        },

        {
            name: "McMurdo",
            x: 1.25,
            z: 0.85,
            temperature: -18.4
        },

        {
            name: "Amundsen-Scott",
            x: 0.10,
            z: -0.45,
            temperature: -32.1
        },

        {
            name: "Concordia",
            x: -0.95,
            z: -1.05,
            temperature: -29.8
        },

        {
            name: "Vostok",
            x: 0.95,
            z: -1.35,
            temperature: -34.2
        },

        {
            name: "Rothera",
            x: -1.95,
            z: -0.75,
            temperature: -14.7
        }
    ];


    stationData.forEach(
        station => {

            createStationNode(station);

        }
    );
}


// ============================================================
// CREATE STATION NODE
// ============================================================

function createStationNode(station) {

    const stationGroup =
        new THREE.Group();


    // --------------------------------------------------------
    // MAIN NODE
    // --------------------------------------------------------

    const nodeGeometry =
        new THREE.SphereGeometry(
            0.075,
            20,
            20
        );


    const nodeMaterial =
        new THREE.MeshBasicMaterial({

            color: 0x159ac0
        });


    const node =
        new THREE.Mesh(
            nodeGeometry,
            nodeMaterial
        );


    node.position.set(
        station.x,
        0.24,
        station.z
    );


    stationGroup.add(node);


    // --------------------------------------------------------
    // OUTER SIGNAL RING
    // --------------------------------------------------------

    const ringGeometry =
        new THREE.RingGeometry(
            0.095,
            0.125,
            32
        );


    const ringMaterial =
        new THREE.MeshBasicMaterial({

            color: 0x55bfd4,

            transparent: true,

            opacity: 0.55,

            side: THREE.DoubleSide
        });


    const ring =
        new THREE.Mesh(
            ringGeometry,
            ringMaterial
        );


    ring.rotation.x =
        -Math.PI / 2;


    ring.position.set(
        station.x,
        0.16,
        station.z
    );


    stationGroup.add(ring);


    // --------------------------------------------------------
    // VERTICAL SIGNAL
    // --------------------------------------------------------

    const lineGeometry =
        new THREE.BufferGeometry().setFromPoints([

            new THREE.Vector3(
                station.x,
                0.18,
                station.z
            ),

            new THREE.Vector3(
                station.x,
                0.65,
                station.z
            )
        ]);


    const lineMaterial =
        new THREE.LineBasicMaterial({

            color: 0x56bfd4,

            transparent: true,

            opacity: 0.48
        });


    const signalLine =
        new THREE.Line(
            lineGeometry,
            lineMaterial
        );


    stationGroup.add(signalLine);


    // --------------------------------------------------------
    // STATION LABEL
    // --------------------------------------------------------

    const label =
        createStationLabel(
            station.name
        );


    label.position.set(
        station.x,
        0.72,
        station.z
    );


    stationGroup.add(label);


    twinGroup.add(stationGroup);

    twinStations.push({
        group: stationGroup,
        ring: ring,
        data: station
    });
}


// ============================================================
// STATION LABEL
// ============================================================

function createStationLabel(text) {

    const canvas =
        document.createElement("canvas");

    canvas.width = 512;
    canvas.height = 96;


    const context =
        canvas.getContext("2d");


    context.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );


    context.fillStyle =
        "rgba(255,255,255,0.88)";


    context.roundRect(
        8,
        8,
        496,
        80,
        14
    );


    context.fill();


    context.fillStyle =
        "#16445a";


    context.font =
        "bold 30px Arial";


    context.textAlign =
        "center";


    context.textBaseline =
        "middle";


    context.fillText(
        text,
        256,
        48
    );


    const texture =
        new THREE.CanvasTexture(
            canvas
        );


    const material =
        new THREE.SpriteMaterial({

            map: texture,

            transparent: true,

            depthWrite: false
        });


    const sprite =
        new THREE.Sprite(
            material
        );


    sprite.scale.set(
        1.15,
        0.22,
        1
    );


    return sprite;
}


// ============================================================
// ICE RINGS
// ============================================================

function createIceRings() {

    const ringSizes = [
        2.95,
        2.70,
        2.40
    ];


    ringSizes.forEach(
        (radius, index) => {

            const geometry =
                new THREE.RingGeometry(
                    radius,
                    radius + 0.012,
                    96
                );


            const material =
                new THREE.MeshBasicMaterial({

                    color:
                        index === 0
                            ? 0x8dd8e6
                            : 0xb7e8f0,

                    transparent: true,

                    opacity:
                        index === 0
                            ? 0.65
                            : 0.35,

                    side: THREE.DoubleSide
                });


            const ring =
                new THREE.Mesh(
                    geometry,
                    material
                );


            ring.rotation.x =
                -Math.PI / 2;


            ring.position.y =
                0.035;


            twinGroup.add(ring);
        }
    );
}


// ============================================================
// MOUSE / TOUCH INTERACTION
// ============================================================

function setupInteraction(container) {

    const canvas =
        twinRenderer.domElement;


    // --------------------------------------------------------
    // MOUSE DOWN
    // --------------------------------------------------------

    canvas.addEventListener(
        "mousedown",
        event => {

            isDragging = true;

            previousMouseX =
                event.clientX;

            previousMouseY =
                event.clientY;
        }
    );


    // --------------------------------------------------------
    // MOUSE MOVE
    // --------------------------------------------------------

    window.addEventListener(
        "mousemove",
        event => {

            if (!isDragging) return;


            const deltaX =
                event.clientX -
                previousMouseX;


            const deltaY =
                event.clientY -
                previousMouseY;


            rotationY +=
                deltaX * 0.008;


            rotationX +=
                deltaY * 0.004;


            rotationX =
                Math.max(
                    -0.55,
                    Math.min(
                        0.55,
                        rotationX
                    )
                );


            previousMouseX =
                event.clientX;

            previousMouseY =
                event.clientY;
        }
    );


    // --------------------------------------------------------
    // MOUSE UP
    // --------------------------------------------------------

    window.addEventListener(
        "mouseup",
        () => {

            isDragging = false;

        }
    );


    // --------------------------------------------------------
    // WHEEL ZOOM
    // --------------------------------------------------------

    canvas.addEventListener(
        "wheel",
        event => {

            event.preventDefault();


            twinCamera.position.z +=
                event.deltaY * 0.004;


            twinCamera.position.z =
                Math.max(
                    5.0,
                    Math.min(
                        10.0,
                        twinCamera.position.z
                    )
                );
        },
        { passive: false }
    );
}


// ============================================================
// RESET VIEW
// ============================================================

function resetDigitalTwinView() {

    rotationX = 0;

    rotationY = 0;

    twinCamera.position.set(
        0,
        5.2,
        7.5
    );

    twinCamera.lookAt(
        0,
        0,
        0
    );
}


// ============================================================
// ANIMATION
// ============================================================

function animateDigitalTwin() {

    requestAnimationFrame(
        animateDigitalTwin
    );


    if (!twinRenderer ||
        !twinScene ||
        !twinCamera) {

        return;
    }


    // Smooth user rotation
    twinGroup.rotation.y =
        rotationY;


    twinGroup.rotation.x =
        rotationX - 0.08;


    // Station pulse
    const time =
        performance.now() * 0.003;


    twinStations.forEach(
        station => {

            const pulse =
                1 +
                Math.sin(
                    time +
                    station.data.x * 2
                ) * 0.18;


            station.ring.scale.set(
                pulse,
                pulse,
                pulse
            );
        }
    );


    twinRenderer.render(
        twinScene,
        twinCamera
    );
}


// ============================================================
// RESPONSIVE
// ============================================================

function resizeDigitalTwin() {

    const container =
        document.getElementById(
            "digital-twin"
        );


    if (!container ||
        !twinRenderer ||
        !twinCamera) {

        return;
    }


    const width =
        container.clientWidth;


    const height =
        container.clientHeight;


    if (!width || !height) return;


    twinCamera.aspect =
        width / height;


    twinCamera.updateProjectionMatrix();


    twinRenderer.setSize(
        width,
        height
    );
}


// ============================================================
// START
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        if (
            typeof THREE !==
            "undefined"
        ) {

            initDigitalTwin();

        } else {

            console.error(
                "POLAR: Three.js failed to load."
            );
        }
    }
);