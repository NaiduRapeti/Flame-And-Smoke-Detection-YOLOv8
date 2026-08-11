# Fire & Smoke Detection System

A real-time fire and smoke detection system using YOLOv8 and Flask. This application can detect fire and smoke in images and live video streams with high accuracy.

## 🚀 Features

- Real-time fire and smoke detection
- Web interface for easy interaction
- Support for both image uploads and live camera feed
- Responsive design that works on desktop and mobile devices
- Detailed detection results with confidence scores

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.8 or higher
- pip (Python package manager)
- Webcam (for live detection)
- Modern web browser (Chrome, Firefox, Edge, or Safari)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/fire-smoke-detection.git
   cd fire-smoke-detection
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🏃‍♂️ How to Run

1. **Start the application**
   ```bash
   python fire_app.py
   ```

2. **Access the web interface**
   Open your web browser and navigate to:
   ```
   http://localhost:5001
   ```

## 🖥️ Using the Application

### Image Detection
1. Click on the "Choose File" button to upload an image
2. The system will process the image and highlight any detected fire or smoke
3. Results will show the confidence level of each detection

### Live Detection
1. Click on the "Start Detection" button to begin live detection
2. Allow camera access when prompted by your browser
3. The system will analyze the video feed in real-time
4. Click "Stop Detection" to end the live session

## 📁 Project Structure

```
Fire & Smoke Detection/
├── static/                 # Static files (CSS, JS, images)
│   ├── css/
│   └── js/
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── detect.html
│   ├── about.html
│   ├── 404.html
│   └── 500.html
├── uploads/               # Temporary storage for uploaded images
├── best.pt               # Pre-trained YOLO model
├── fire_app.py           # Main application file
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🛠️ Customization

### Model
- The application uses a pre-trained YOLOv8 model (`best.pt`)
- To use your own trained model, replace `best.pt` with your model file

### Configuration
- Edit `fire_app.py` to modify:
  - Host and port settings
  - Upload folder location
  - Model parameters

## 🌐 Web Interface

The web interface is built with:
- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python (Flask)
- **Computer Vision**: OpenCV, YOLOv8

## 🔒 Security Notes

- The application runs locally by default
- For production use:
  - Use HTTPS
  - Implement user authentication
  - Set proper file upload restrictions
  - Keep dependencies updated

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- YOLOv8 by Ultralytics
- Flask web framework
- OpenCV for computer vision
- All open-source libraries used in this project
