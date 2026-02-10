const video = document.getElementById("camera");
let stream = null;
let running = false;

const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");

let history = [];


/* ======================
   CAMERA
====================== */

async function startCamera() {
    if (running) return;

    stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false
    });

    video.srcObject = stream;
    await video.play();

    running = true;
    loop();
}

function stopCamera() {
    running = false;

    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
}


/* ======================
   LOOP (แทน setInterval)
====================== */

async function loop() {
    while (running) {
        await captureAndSend();
        await new Promise(r => setTimeout(r, 1500)); // 1.5s safer
    }
}


async function captureAndSend() {
    if (!video.videoWidth) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0);

    const blob = await new Promise(r =>
        canvas.toBlob(r, "image/jpeg", 0.7)
    );

    const form = new FormData();
    form.append("image", blob);

    const res = await fetch("/detect", {
        method: "POST",
        body: form
    });

    if (!res.ok) return;

    const imgBlob = await res.blob();

    if (video.poster) URL.revokeObjectURL(video.poster);
    video.poster = URL.createObjectURL(imgBlob);
}


/* ======================
   DASHBOARD
====================== */

async function loadDashboard() {
    const res = await fetch("/stats");
    if (!res.ok) return;

    const data = await res.json();

    document.getElementById("count").innerText = data.no_helmet;
    document.getElementById("date").innerText = data.date;

    history.push(data.no_helmet);
    if (history.length > 30) history.shift();

    drawChart();
}

setInterval(loadDashboard, 2000);


function drawChart() {
    const c = document.getElementById("chart");
    const ctx = c.getContext("2d");

    ctx.clearRect(0, 0, c.width, c.height);

    const max = Math.max(...history, 1);

    ctx.beginPath();

    history.forEach((v, i) => {
        const x = i * (c.width / history.length);
        const y = c.height - (v / max) * c.height;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.stroke();
}


/* ======================
   NAV
====================== */

function showPage(page) {
    ["live", "guide", "dashboard"].forEach(p => {
        document.getElementById("page-" + p).style.display = "none";
    });

    document.getElementById("page-" + page).style.display = "block";
}


document.getElementById("btn-start").onclick = startCamera;
document.getElementById("btn-stop").onclick = stopCamera;
