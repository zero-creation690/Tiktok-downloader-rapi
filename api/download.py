import os
import tempfile
import asyncio
import functools
import mimetypes
from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.common import PostProcessor
from fastapi import FastAPI, HTTPException, status, Request
from starlette.responses import FileResponse

# The Vercel execution environment limits filesystem access, but /tmp is writable.
TEMP_DIR = tempfile.gettempdir()

# --- Custom Hook to Capture Final Filename and Clean Up ---
class FilenameCapturePP(PostProcessor):
    """
    A post-processor that intercepts the final output filename determined by yt-dlp.
    This is necessary because yt-dlp determines the final name *after* initialization.
    """
    def __init__(self, directory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = None
        self.directory = directory

    def run(self, info):
        # The 'filepath' is set by yt-dlp after determining the best format/output name
        if info.get('filepath'):
            self.filename = info['filepath']
        
        # Ensure the filename is within the temporary directory
        if self.filename and not self.filename.startswith(self.directory):
            # This handles cases where yt-dlp prepends default paths; we ensure it's in /tmp
            self.filename = os.path.join(self.directory, os.path.basename(self.filename))
        
        return [], info

# --- Vercel/FastAPI Setup ---
# The entry point must be an ASGI application named 'app'
app = FastAPI(
    title="TikTok Downloader API",
    description="Serverless API for downloading TikTok videos using yt-dlp.",
    version="1.0.0"
)

# --- Core Download Logic ---
def perform_download(url: str) -> str:
    """
    Synchronous function to execute yt-dlp. It returns the path to the 
    downloaded file on success, or raises an exception.
    """
    
    # 1. Generate a unique temporary filename prefix
    # We use a path inside /tmp and let yt-dlp name the file
    # We use a uuid in the name to prevent filename clashes in concurrent requests
    temp_prefix = os.path.join(TEMP_DIR, f'tiktok_dl_%(title)s.%(ext)s')
    
    # 2. Setup the Filename Capture Hook
    capture_pp = FilenameCapturePP(TEMP_DIR)

    # 3. Define yt-dlp options
    ydl_opts = {
        # General options
        'format': 'best', # Request best available format (often works for TikTok as single file)
        'noplaylist': True,
        'verbose': False,
        'quiet': True,
        'no_warnings': True,
        'logger': None, # Suppress all yt-dlp logging output

        # Filesystem options
        'outtmpl': temp_prefix, # Output template path
        'cachedir': False, # Disable caching
        'cookiefile': False, # Disable cookie file usage
        'writedescription': False,
        'writeinfojson': False,
        
        # Post-processing options (to capture the filename)
        'postprocessors': [capture_pp],
    }
    
    # 4. Execute the download
    try:
        with YoutubeDL(ydl_opts) as ydl:
            # We must call extract_info with download=True to trigger the download process
            ydl.download([url])

            final_filepath = capture_pp.filename
            
            if not final_filepath or not os.path.exists(final_filepath):
                 raise Exception("Download succeeded but final file path could not be determined or file was not found.")

            return final_filepath

    except Exception as e:
        # Catch and re-raise all exceptions for proper HTTP response handling
        # For security, only return a generic message unless debugging
        raise Exception(f"Failed to download URL. Detail: {e}")


async def run_in_threadpool(func, *args, **kwargs):
    """Runs a synchronous function in a separate thread to prevent blocking the ASGI loop."""
    loop = asyncio.get_event_loop()
    # Use the default thread pool executor (None)
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

# --- API Endpoint Definition ---
@app.get("/api/download")
async def download_video(request: Request):
    """
    Downloads a video from the provided URL and returns it as a file attachment.

    Usage: /api/download?url=<TikTok URL>
    """
    url = request.query_params.get('url')

    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'url' query parameter is required."
        )

    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format. Must start with http:// or https://."
        )

    final_filepath = None
    try:
        # Run the synchronous download function in a threadpool
        final_filepath = await run_in_threadpool(perform_download, url)
        
        # Determine MIME type and output filename
        mime_type, _ = mimetypes.guess_type(final_filepath)
        mime_type = mime_type if mime_type else 'application/octet-stream'

        base_filename = os.path.basename(final_filepath)
        
        # Return the file using FileResponse
        # FileResponse efficiently streams the file and handles headers.
        return FileResponse(
            path=final_filepath,
            media_type=mime_type,
            filename=base_filename,
            # Force download prompt
            headers={"Content-Disposition": f"attachment; filename=\"{base_filename}\""}
        )

    except HTTPException:
        # Re-raise explicit HTTP exceptions (e.g., 400 or 500 from the checks above)
        raise
    except Exception as e:
        # Catch all other exceptions and return a 500
        print(f"FATAL ERROR during download: {e}")
        # Return a generic error to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the download process. Please check the provided URL."
        )
    finally:
        # --- CRITICAL CLEANUP STEP ---
        # Ensure the temporary file is deleted in all cases (success or failure)
        if final_filepath and os.path.exists(final_filepath):
            try:
                os.remove(final_filepath)
                # print(f"Cleaned up file: {final_filepath}")
            except Exception as cleanup_e:
                # Log cleanup failures, but don't fail the user request
                print(f"Failed to clean up file {final_filepath}: {cleanup_e}")

# This is the handler function used by Vercel for the Python runtime
# Vercel automatically finds the ASGI 'app' instance in this file.
