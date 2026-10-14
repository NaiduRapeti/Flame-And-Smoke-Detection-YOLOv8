// DOM Elements
const statusEl = document.getElementById("status");
const statusSpinner = document.getElementById("statusSpinner");
const video = document.getElementById("webcam");
const cameraOffPlaceholder = document.getElementById("cameraOffPlaceholder");
const captureBtn = document.getElementById("captureBtn");
const startStopBtn = document.getElementById("startStopBtn");
const contBtn = document.getElementById("contBtn");
const stopAuto = document.getElementById("stopAuto");
const clearBtn = document.getElementById("clearBtn");
const clearResult = document.getElementById("clearResult");
const fileInput = document.getElementById("fileInput");
const resultImg = document.getElementById("resultImg");
const uploadedImage = document.getElementById("uploadedImage");
const uploadedImageContainer = document.getElementById("uploadedImageContainer");
const placeholder = document.getElementById("placeholder");
const downloadLink = document.getElementById("downloadLink");
const uploadForm = document.getElementById("uploadForm");

// State variables
let stream = null;
let autoInterval = null;
let lastAutoTimestamp = 0;
let isCameraOn = false;

// Helper Functions
function setStatus(text, isLoading = false) {
    const statusText = statusEl.querySelector('span:not(.spinner-border)');
    statusText.textContent = text;
    
    if (isLoading) {
        statusSpinner.classList.remove('d-none');
    } else {
        statusSpinner.classList.add('d-none');
    }
}

// Camera Control Functions
async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment'
            } 
        });
        video.srcObject = stream;
        video.style.display = 'block';
        cameraOffPlaceholder.style.display = 'none';
        isCameraOn = true;
        startStopBtn.innerHTML = '<i class="bi bi-camera-video-off me-1"></i> Stop Camera';
        captureBtn.disabled = false;
        contBtn.disabled = false;
        setStatus("Camera is active");
    } catch (err) {
        console.error("Error accessing webcam:", err);
        setStatus("Camera access denied");
        isCameraOn = false;
        startStopBtn.innerHTML = '<i class="bi bi-camera-video me-1"></i> Start Camera';
        captureBtn.disabled = true;
        contBtn.disabled = true;
    }
}

function stopCamera() {
    if (stream) {
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        video.style.display = 'none';
        cameraOffPlaceholder.style.display = 'flex';
        isCameraOn = false;
        startStopBtn.innerHTML = '<i class="bi bi-camera-video me-1"></i> Start Camera';
        captureBtn.disabled = true;
        contBtn.disabled = true;
        setStatus("Camera is off");
    }
}

// Toggle camera on/off
startStopBtn.addEventListener('click', () => {
    if (isCameraOn) {
        stopCamera();
    } else {
        startCamera();
    }
});

// Capture frame from webcam
function captureFrame() {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.8);
}

// Event Listeners
captureBtn.addEventListener('click', () => {
    if (!isCameraOn) return;
    const dataUrl = captureFrame();
    sendImageDataUrl(dataUrl);
});

contBtn.addEventListener('click', () => {
    if (!isCameraOn) return;
    contBtn.style.display = 'none';
    stopAuto.style.display = 'inline-block';
    setStatus("Auto-detection running...", true);
    
    // Capture every 500ms (2 FPS)
    autoInterval = setInterval(() => {
        const now = Date.now();
        if (now - lastAutoTimestamp >= 1000) {
            const dataUrl = captureFrame();
            sendImageDataUrl(dataUrl, true);
            lastAutoTimestamp = now;
        }
    }, 3000);
});

stopAuto.addEventListener('click', () => {
    if (autoInterval) {
        clearInterval(autoInterval);
        autoInterval = null;
    }
    contBtn.style.display = 'inline-block';
    stopAuto.style.display = 'none';
    setStatus("Auto-detection stopped");});

clearBtn.addEventListener('click', () => {
    fileInput.value = '';
    uploadedImage.style.display = 'none';
    uploadedImage.src = '';
});

clearResult.addEventListener('click', () => {
    resultImg.style.display = 'none';
    placeholder.style.display = 'block';
    downloadLink.style.display = 'none';
});

// Upload form handling
uploadForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    
    if (!file) {
        setStatus("Please select an image file");
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        // Display the uploaded image
        uploadedImage.src = e.target.result;
        uploadedImage.style.display = 'block';
        uploadedImageContainer.style.display = 'block';
        
        // Process the image
        sendImageDataUrl(e.target.result);
    };
    reader.readAsDataURL(file);
});

// Send image data to server for processing
async function sendImageDataUrl(dataUrl, isAuto = false) {
    if (!isAuto) {
        setStatus("Processing...", true);
    }

    try {
        const response = await fetch('/detect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: dataUrl })
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        displayResultFromB64(data.image);
        setStatus(isAuto ? "Auto-detection running" : "Detection complete");
    } catch (error) {
        console.error('Error:', error);
        setStatus(`Error: ${error.message}`);
    }
}

// Display the processed image with detections
function displayResultFromB64(b64) {
    resultImg.src = `data:image/jpeg;base64,${b64}`;
    resultImg.style.display = 'block';
    placeholder.style.display = 'none';
    
    // Update download link
    downloadLink.href = `data:image/jpeg;base64,${b64}`;
    downloadLink.style.display = 'inline-block';
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Set initial state
    captureBtn.disabled = true;
    contBtn.disabled = true;
    
    // Set up camera off placeholder
    cameraOffPlaceholder.innerHTML = `
        <div class="text-center">
            <i class="bi bi-camera-video-off fs-1 mb-2"></i>
            <p class="mb-0">Camera is off</p>
            <small class="text-muted">Click 'Start Camera' to begin</small>
        </div>
    `;
});
