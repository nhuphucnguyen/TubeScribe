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

## License

This project is licensed under the MIT License - see the LICENSE file for details.
