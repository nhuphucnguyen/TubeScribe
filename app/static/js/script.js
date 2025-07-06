document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const youtubeUrlInput = document.getElementById('youtube-url');
    const fetchInfoBtn = document.getElementById('fetch-info-btn');
    const errorContainer = document.getElementById('error-container');
    const videoInfo = document.getElementById('video-info');
    const videoTitle = document.getElementById('video-title');
    const formatsContainer = document.getElementById('formats-container');
    const downloadBtn = document.getElementById('download-btn');
    const downloadProgress = document.getElementById('download-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const downloadStatus = document.getElementById('download-status');
    const downloadComplete = document.getElementById('download-complete');
    const downloadFileBtn = document.getElementById('download-file-btn');
    const newDownloadBtn = document.getElementById('new-download-btn');

    // State
    let currentVideoInfo = null;
    let selectedFormat = null;
    let downloadId = null;
    let statusCheckInterval = null;

    // Event Listeners
    fetchInfoBtn.addEventListener('click', handleFetchInfo);
    downloadBtn.addEventListener('click', handleDownload);
    newDownloadBtn.addEventListener('click', resetInterface);
    
    // Functions
    async function handleFetchInfo() {
        const url = youtubeUrlInput.value.trim();
        
        if (!url) {
            showError('Please enter a YouTube URL');
            return;
        }
        
        if (!isValidYoutubeUrl(url)) {
            showError('Please enter a valid YouTube URL');
            return;
        }
        
        try {
            showError(''); // Clear any previous errors
            fetchInfoBtn.disabled = true;
            fetchInfoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            
            const response = await fetch('/api/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch video information');
            }
            
            const data = await response.json();
            currentVideoInfo = data;
            
            // Display video info
            videoTitle.textContent = data.title;
            displayFormats(data.formats);
            
            videoInfo.classList.remove('hidden');
            
        } catch (error) {
            showError(error.message);
        } finally {
            fetchInfoBtn.disabled = false;
            fetchInfoBtn.innerHTML = 'Get Video Info';
        }
    }
    
    function displayFormats(formats) {
        formatsContainer.innerHTML = '';
        
        if (formats.length === 0) {
            formatsContainer.innerHTML = '<p>No formats available for this video</p>';
            downloadBtn.disabled = true;
            return;
        }
        
        formats.forEach((format, index) => {
            const formatItem = document.createElement('div');
            formatItem.className = 'format-item';
            formatItem.dataset.formatId = format.format_id;
            
            let formatTitle = '';
            let formatInfo = '';
            
            // Handle video formats
            if (format.resolution) {
                formatTitle = `${format.resolution} (${format.ext})`;
                
                // Format file size if available
                let sizeInfo = '';
                if (format.filesize) {
                    sizeInfo = ` - ${formatFileSize(format.filesize)}`;
                }
                
                formatInfo = `${format.format_note || ''}${sizeInfo}`;
            } 
            // Handle audio formats
            else {
                formatTitle = `Audio (${format.ext})`;
                
                let sizeInfo = '';
                if (format.filesize) {
                    sizeInfo = ` - ${formatFileSize(format.filesize)}`;
                }
                
                formatInfo = `${format.format_note || 'Audio only'}${sizeInfo}`;
            }
            
            formatItem.innerHTML = `
                <div class="format-title">${formatTitle}</div>
                <div class="format-info">${formatInfo}</div>
            `;
            
            formatItem.addEventListener('click', () => {
                // Remove selected class from all formats
                document.querySelectorAll('.format-item').forEach(item => {
                    item.classList.remove('selected');
                });
                
                // Add selected class to clicked format
                formatItem.classList.add('selected');
                selectedFormat = format.format_id;
                downloadBtn.disabled = false;
            });
            
            formatsContainer.appendChild(formatItem);
            
            // Select the first format by default
            if (index === 0) {
                formatItem.click();
            }
        });
    }
    
    async function handleDownload() {
        if (!currentVideoInfo || !selectedFormat) {
            showError('Please select a format first');
            return;
        }
        
        try {
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting Download...';
            
            const formData = new FormData();
            formData.append('url', youtubeUrlInput.value.trim());
            formData.append('format_id', selectedFormat);
            
            const response = await fetch('/api/download', {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start download');
            }
            
            const data = await response.json();
            downloadId = data.download_id;
            
            // Show download progress
            videoInfo.classList.add('hidden');
            downloadProgress.classList.remove('hidden');
            
            // Start checking download status
            startStatusCheck();
            
        } catch (error) {
            showError(error.message);
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download';
        }
    }
    
    function startStatusCheck() {
        // Clear any existing interval
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        // Check status immediately
        checkDownloadStatus();
        
        // Then check every 1 second
        statusCheckInterval = setInterval(checkDownloadStatus, 1000);
    }
    
    async function checkDownloadStatus() {
        try {
            const response = await fetch(`/api/status/${downloadId}`);
            
            if (!response.ok) {
                throw new Error('Failed to get download status');
            }
            
            const data = await response.json();
            
            // Update progress
            updateProgress(data);
            
            // If download is completed or failed, stop checking
            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(statusCheckInterval);
                
                if (data.status === 'completed') {
                    downloadComplete.classList.remove('hidden');
                    downloadFileBtn.addEventListener('click', () => {
                        window.location.href = `/api/download/${downloadId}`;
                    });
                }
            }
            
        } catch (error) {
            console.error('Error checking download status:', error);
        }
    }
    
    function updateProgress(statusData) {
        const { status, progress, error } = statusData;
        
        // Update progress bar
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress.toFixed(1)}%`;
        
        // Update status message
        switch (status) {
            case 'downloading':
                downloadStatus.textContent = 'Downloading video...';
                break;
            case 'processing':
                downloadStatus.textContent = 'Processing video...';
                break;
            case 'completed':
                downloadStatus.textContent = 'Download completed!';
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                break;
            case 'failed':
                downloadStatus.textContent = `Download failed: ${error || 'Unknown error'}`;
                progressBar.style.backgroundColor = 'var(--error-color)';
                break;
            default:
                downloadStatus.textContent = status;
        }
    }
    
    function resetInterface() {
        // Reset UI
        youtubeUrlInput.value = '';
        videoInfo.classList.add('hidden');
        downloadProgress.classList.add('hidden');
        downloadComplete.classList.add('hidden');
        errorContainer.style.display = 'none';
        
        // Reset state
        currentVideoInfo = null;
        selectedFormat = null;
        downloadId = null;
        
        // Reset button states
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download';
        fetchInfoBtn.disabled = false;
        
        // Clear any running interval
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            statusCheckInterval = null;
        }
    }
    
    function showError(message) {
        if (message) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
        } else {
            errorContainer.textContent = '';
            errorContainer.style.display = 'none';
        }
    }
    
    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
        return youtubeRegex.test(url);
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
});
