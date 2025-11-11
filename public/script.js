function load_map(element_id, coordinates, shape) {
    var map = L.map(element_id, {
        dragging: false,
        touchZoom: false,
        doubleClickZoom: false,
        scrollWheelZoom: false,
        boxZoom: false,
        keyboard: false,
        zoomControl: false
    }).setView(coordinates, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // shape is already an object
    L.geoJSON(shape).addTo(map);
}

function new_suburb_pair() {
    fetch("/get_suburb_pair")
        .then(response => response.json())
        .then(data => {
            document.getElementById("suburb0").innerText = data[0]["name"];
            document.getElementById("suburb1").innerText = data[1]["name"];
            
            document.getElementById("suburb0-map").outerHTML = '<div id="suburb0-map" class=map></div>';
            document.getElementById("suburb1-map").outerHTML = '<div id="suburb1-map" class=map></div>';

            Promise.all([
                fetch(data[0]["shape_url"]).then(res => res.json()),
                fetch(data[1]["shape_url"]).then(res => res.json())
            ]).then(shapes => {
                console.log(data[0]["center"]["coordinates"]);
                load_map("suburb0-map", [data[0]["center"]["coordinates"][1], data[0]["center"]["coordinates"][0]], shapes[0]);
                load_map("suburb1-map", [data[1]["center"]["coordinates"][1], data[1]["center"]["coordinates"][0]], shapes[1]);
            });
    });
}

function vote(winner, loser) {
    fetch("/vote", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ winner: winner, loser: loser })
    }).then(() => {
        new_suburb_pair();
    });
}

document.querySelectorAll(".button-card").forEach((card, index) => {
    card.addEventListener("click", () => {
        const suburb0 = document.getElementById("suburb0").innerText;
        const suburb1 = document.getElementById("suburb1").innerText;

        if (index === 0) {
            vote(suburb0, suburb1);
        } else {
            vote(suburb1, suburb0);
        }
    });
});

document.addEventListener("DOMContentLoaded", () => {
    new_suburb_pair();
});