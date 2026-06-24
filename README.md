# PDF/Image Data Extraction System

A Flask web application that extracts data from PDFs and images using Google's Gemini API and returns structured JSON directly in the browser.

## Features

### 🚀 Core Functionality
- **AI-Powered Data Extraction**: Uses Gemini 2.5 Flash to extract structured data from PDFs and images
- **Structured JSON Output**: Displays the extracted JSON directly in the UI
- **No Predefined Schema**: Adapts to any document format

### 🎨 User Interface
- Modern dark theme with gradient accents
- Inline JSON preview with copy support
- Responsive design

## Installation

### Prerequisites
- Python 3.8+
- Google Gemini API Key

### Setup Steps

1. **Clone or download the project**
   ```bash
   cd "c:/Users/tz8e/OneDrive/Desktop/intenship project/jpeg1"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   
   Edit `.env` and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   
   Open your browser and navigate to: `http://127.0.0.1:5000`

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (with defaults)
FLASK_SECRET_KEY=your-secret-key-change-this
FLASK_DEBUG=True
DATABASE_NAME=erp_data.db
UPLOAD_FOLDER=uploads
MAX_FILE_SIZE_MB=16
```

## Usage

### 1. Upload Document
- Click the upload area or drag & drop a PDF or image
- Supported formats: PDF, PNG, JPG, JPEG, GIF, BMP, TIFF
- Max file size: 16MB (configurable)

### 2. View JSON
After upload, the extracted JSON is shown directly on the page.

### 3. Copy or Use the Output
Copy the JSON and feed it into your own workflow or downstream system.

## Database Structure

There is no database table creation in this version. The app only returns extracted JSON.

## Project Structure

```
jpeg1/
├── app.py                 # Flask application & API routes
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
├── uploads/              # Uploaded files (auto-created)
├── static/
│   ├── style.css         # Styles
│   └── script.js         # Upload page logic
└── templates/
   └── index.html        # Upload page
```

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - Upload and process document
- `GET /health` - Health check endpoint

## Technologies Used

- **Backend**: Flask (Python)
- **AI**: Google Generative AI (Gemini 2.5 Flash)
- **Frontend**: HTML, CSS, JavaScript
- **Environment**: python-dotenv

## Security Notes

⚠️ **Important**:
- Never commit `.env` file to version control
- Keep your Gemini API key secret
- Change `FLASK_SECRET_KEY` in production
- Use proper authentication in production environments

## License

This project is for educational and development purposes.

## Support

For issues or questions, please check:
1. Ensure `.env` file exists with valid `GEMINI_API_KEY`
2. Check that all dependencies are installed
3. Verify Python version is 3.8+
