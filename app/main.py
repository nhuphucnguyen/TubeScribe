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
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get video info: {str(e)}")


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
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': str(download_path / '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
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
    
    # Filter formats for better presentation
    formats = []
    seen_resolution = set()
    
    for f in info.get('formats', []):
        if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none':
            resolution = f.get('resolution', 'unknown')
            ext = f.get('ext', 'unknown')
            format_id = f.get('format_id', '')
            
            format_key = f"{resolution}_{ext}"
            if format_key not in seen_resolution and 'audio only' not in resolution:
                seen_resolution.add(format_key)
                formats.append({
                    'format_id': format_id,
                    'resolution': resolution,
                    'ext': ext,
                    'filesize': f.get('filesize', 0),
                    'format_note': f.get('format_note', '')
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
    
    return DownloadResponse(
        download_id=download_id,
        title=info.get('title', 'Unknown Title'),
        formats=sorted(formats, key=lambda x: x.get('filesize', 0) if x.get('filesize') else 0, reverse=True) + audio_formats
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
