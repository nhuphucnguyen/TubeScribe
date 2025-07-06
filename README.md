# TubeScribe - YouTube Video Downloader

TubeScribe is a web application that allows users to download YouTube videos to their devices using the powerful yt-dlp library.

## Features

- Fetch video information from YouTube URLs
- Display available video formats and resolutions
- Download videos in various formats
- Real-time download progress tracking
- Support for audio-only downloads
- Clean and responsive user interface

## Requirements

- Python 3.8 or higher
- FastAPI
- yt-dlp
- Other dependencies listed in requirements.txt

## Installation

### Standard Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tubescribe.git
   cd tubescribe
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python run.py
   ```

4. Open a web browser and navigate to:
   ```
   http://localhost:8000
   ```

### Docker Installation

You can also run TubeScribe using Docker:

1. Build and start the container using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Or build and run the Docker container manually:
   ```bash
   docker build -t tubescribe .
   docker run -p 8000:8000 -v $(pwd)/downloads:/app/downloads tubescribe
   ```

3. Open a web browser and navigate to:
   ```
   http://localhost:8000
   ```

## Usage

1. Enter a valid YouTube URL in the input field
2. Click "Get Video Info" to fetch available formats
3. Select your preferred format/resolution
4. Click "Download" to start the download process
5. Once completed, click "Save to Device" to download the file to your computer

## Important Notes

- This application is for personal use only
- Please respect copyright laws and YouTube's terms of service
- Large video files may take a considerable amount of time to download depending on your internet connection

## Troubleshooting

If you encounter any issues:

1. Make sure you have the latest version of yt-dlp installed
   ```bash
   pip install -U yt-dlp
   ```

2. Check that the YouTube URL is valid and accessible
3. Ensure you have sufficient disk space for downloads
4. Some videos may be restricted and not available for download

### Docker Troubleshooting

1. If you have issues with permissions:
   ```bash
   # Reset permissions on the downloads directory
   docker-compose down
   sudo chown -R $(id -u):$(id -g) downloads
   docker-compose up -d
   ```

2. To view logs:
   ```bash
   docker-compose logs -f
   ```

3. To rebuild the container after changes:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
