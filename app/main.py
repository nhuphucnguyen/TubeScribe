from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import uuid
import yt_dlp
import re
import shutil
from pathlib import Path
import asyncio
from typing import Optional, List, Dict, Any

app = FastAPI(title="TubeScribe - YouTube Video Downloader")

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Create downloads directory if it doesn't exist
downloads_dir = Path("downloads")
downloads_dir.mkdir(exist_ok=True)

# Models
class DownloadRequest(BaseModel):
    url: str
    format: str = "mp4"  # Default format

class DownloadResponse(BaseModel):
    download_id: str
    title: str
    formats: List[Dict[str, Any]]

class DownloadStatus(BaseModel):
    download_id: str
    status: str
    progress: float = 0
    file_path: Optional[str] = None
    error: Optional[str] = None

# Store download progress
download_tasks = {}


def validate_youtube_url(url: str) -> bool:
    """Validate if the URL is a proper YouTube URL."""
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    return bool(re.match(youtube_regex, url))


def get_video_info(url: str) -> dict:
    """Get video information using yt-dlp."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'bestvideo+bestaudio/best',  # Request all available formats
        'youtube_include_dash_manifest': True,  # Include DASH manifests
        'ignore_no_formats_error': True,
        'extract_flat': False,
        'check_formats': True,
        'noplaylist': True,  # Only get info for the video, not the playlist
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get video info: {str(e)}")


def _download_with_ytdlp(ydl_opts, url):
    """Download a video with yt-dlp in a separate thread."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return {'info': info, 'ydl': ydl}

async def download_video(download_id: str, url: str, format_id: str):
    """Download a video asynchronously and update its status."""
    download_path = downloads_dir / download_id
    download_path.mkdir(exist_ok=True)
    
    download_tasks[download_id] = DownloadStatus(
        download_id=download_id,
        status="downloading",
        progress=0
    )
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes'] > 0:
                progress = d['downloaded_bytes'] / d['total_bytes'] * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                progress = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
            else:
                progress = 0
                
            download_tasks[download_id].progress = round(progress, 2)
        
        elif d['status'] == 'finished':
            download_tasks[download_id].status = "processing"
            download_tasks[download_id].progress = 100
    
    # For special format selectors like 'best' or 'bestvideo+bestaudio'
    # we need to ensure the format string is correct
    format_string = format_id
    postprocessor_args = {}
    
    # Configure different format selectors based on the user's choice
    if format_id == 'bestvideo+bestaudio':
        # Get the best video and best audio and merge them
        # This provides the highest quality possible
        format_string = 'bestvideo+bestaudio/best'
    elif format_id == 'best':
        # Get the best combined format (pre-merged)
        format_string = 'best/bestvideo+bestaudio'
    elif format_id == '4K':
        # Specifically try to get 4K quality
        format_string = 'bestvideo[height>=2160]+bestaudio/best[height>=2160]'
    elif format_id == '1080p':
        # Specifically try to get 1080p quality
        format_string = 'bestvideo[height>=1080][height<2160]+bestaudio/best[height>=1080][height<2160]'
    elif format_id == '720p':
        # Specifically try to get 720p quality
        format_string = 'bestvideo[height>=720][height<1080]+bestaudio/best[height>=720][height<1080]'
    elif format_id == 'mp4':
        # Specifically try to get mp4 format
        format_string = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    elif format_id == 'webm':
        # Specifically try to get webm format
        format_string = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]'
    
    ydl_opts = {
        'format': format_string,
        'outtmpl': str(download_path / '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'merge_output_format': 'mp4',  # Force merge to mp4 for compatibility
        'postprocessor_args': postprocessor_args,
        'prefer_ffmpeg': True,
        'noplaylist': True,  # Only download the video, not the playlist
    }
    
    # Run the CPU-intensive download operation in a separate thread pool
    # to prevent blocking the asyncio event loop
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: _download_with_ytdlp(ydl_opts, url)
        )
        
        info = result['info']
        ydl = result['ydl']
        
        # Get the downloaded file path
        if 'entries' in info:  # It's a playlist
            file_path = ydl.prepare_filename(info['entries'][0])
        else:  # It's a single video
            file_path = ydl.prepare_filename(info)
        
        # Update extension if it was converted
        if os.path.exists(file_path):
            file_path = file_path
        else:
            # Try to find the file with a different extension
            base_path = os.path.splitext(file_path)[0]
            potential_files = list(download_path.glob(f"{os.path.basename(base_path)}.*"))
            if potential_files:
                file_path = str(potential_files[0])
        
        download_tasks[download_id].status = "completed"
        download_tasks[download_id].file_path = file_path
        
    except Exception as e:
        download_tasks[download_id].status = "failed"
        download_tasks[download_id].error = str(e)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/info")
async def get_info(request: DownloadRequest):
    """Get video information and available formats."""
    if not validate_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    info = get_video_info(request.url)
    
    # Also include best available formats from format selector
    best_formats = []
    
    # Add best video + best audio (highest quality)
    best_formats.append({
        'format_id': 'bestvideo+bestaudio',
        'resolution': 'Maximum Quality',
        'ext': 'mp4',
        'filesize': 0,
        'format_note': 'Best video & audio quality available (largest file)'
    })
    
    # Add specific resolution options
    best_formats.append({
        'format_id': '4K',
        'resolution': '4K (2160p)',
        'ext': 'mp4',
        'filesize': 0,
        'format_note': '4K quality (if available)'
    })
    
    best_formats.append({
        'format_id': '1080p',
        'resolution': 'Full HD (1080p)',
        'ext': 'mp4',
        'filesize': 0,
        'format_note': 'Full HD quality'
    })
    
    best_formats.append({
        'format_id': '720p',
        'resolution': 'HD (720p)',
        'ext': 'mp4',
        'filesize': 0,
        'format_note': 'HD quality (smaller file)'
    })
    
    # Add specific format options
    best_formats.append({
        'format_id': 'mp4',
        'resolution': 'Best MP4',
        'ext': 'mp4',
        'filesize': 0,
        'format_note': 'Best quality in MP4 format'
    })
    
    best_formats.append({
        'format_id': 'webm',
        'resolution': 'Best WebM',
        'ext': 'webm',
        'filesize': 0,
        'format_note': 'Best quality in WebM format'
    })
    
    # Add best format (balanced quality)
    best_formats.append({
        'format_id': 'best',
        'resolution': 'Balanced Quality',
        'ext': 'mp4',
        'filesize': 0,
        'format_note': 'Good balance of quality and file size'
    })
    
    # Filter specific formats for better presentation
    formats = []
    seen_resolution = set()
    
    for f in info.get('formats', []):
        if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none':
            resolution = f.get('resolution', 'unknown')
            ext = f.get('ext', 'unknown')
            format_id = f.get('format_id', '')
            height = f.get('height', 0)
            
            format_key = f"{resolution}_{ext}"
            if format_key not in seen_resolution and 'audio only' not in resolution and height > 0:
                seen_resolution.add(format_key)
                formats.append({
                    'format_id': format_id,
                    'resolution': resolution,
                    'ext': ext,
                    'filesize': f.get('filesize', 0),
                    'format_note': f.get('format_note', ''),
                    'height': height  # Store height for sorting
                })
    
    # Also add audio-only formats
    audio_formats = []
    seen_audio = set()
    
    for f in info.get('formats', []):
        if f.get('vcodec', 'none') == 'none' and f.get('acodec', 'none') != 'none':
            ext = f.get('ext', 'unknown')
            format_id = f.get('format_id', '')
            
            if ext not in seen_audio:
                seen_audio.add(ext)
                audio_formats.append({
                    'format_id': format_id,
                    'ext': ext,
                    'filesize': f.get('filesize', 0),
                    'format_note': f"Audio {f.get('format_note', '')}"
                })
    
    download_id = str(uuid.uuid4())
    
    # Sort by height (resolution) in descending order
    sorted_formats = sorted(formats, key=lambda x: x.get('height', 0), reverse=True)
    
    # Remove height field from result as it's not needed in the frontend
    for fmt in sorted_formats:
        if 'height' in fmt:
            del fmt['height']
    
    # Combine formats with best formats first, then sorted regular formats, then audio
    all_formats = best_formats + sorted_formats + audio_formats
    
    return DownloadResponse(
        download_id=download_id,
        title=info.get('title', 'Unknown Title'),
        formats=all_formats
    )


@app.post("/api/download")
async def download(url: str = Form(...), format_id: str = Form(...)):
    """Start a video download process."""
    if not validate_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    download_id = str(uuid.uuid4())
    
    # Start download process in background
    asyncio.create_task(download_video(download_id, url, format_id))
    
    return {"download_id": download_id}


@app.get("/api/status/{download_id}")
async def get_status(download_id: str):
    """Get the status of a download."""
    if download_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return download_tasks[download_id]


@app.get("/api/download/{download_id}")
async def serve_download(download_id: str):
    """Serve the downloaded file."""
    if download_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download not found")
    
    status = download_tasks[download_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"Download is not completed: {status.status}")
    
    if not status.file_path or not os.path.exists(status.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=status.file_path, 
        filename=os.path.basename(status.file_path),
        media_type="application/octet-stream"
    )


@app.on_event("shutdown")
async def cleanup():
    """Clean up temporary files on shutdown."""
    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
