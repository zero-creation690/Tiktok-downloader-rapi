import requests
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Iterator

# Initialize the FastAPI application
# This 'app' instance will be the handler Vercel invokes.
app = FastAPI()

# --- Utility Functions ---

def get_video_stream(url: str) -> Iterator[bytes]:
    """
    Simulates fetching and streaming the video content chunk by chunk.
    This function handles the actual request and streaming.
    """
    try:
        # Set stream=True for chunked downloading, crucial for serverless environments.
        response = requests.get(url, stream=True, timeout=30) 
        
        if response.status_code != 200:
            # Raise an error if the content fetching failed
            raise HTTPException(status_code=400, detail=f"Failed to resolve video URL. Status: {response.status_code}")
        
        # Stream the content in 8KB chunks
        for chunk in response.iter_content(chunk_size=8192):
            yield chunk
            
        response.close()

    except requests.exceptions.RequestException as e:
        # Catch network or timeout errors
        raise HTTPException(status_code=500, detail=f"An external request error occurred: {e}")
    except Exception as e:
        # Catch any other unexpected error
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {e}")


@app.get("/")
async def download_tiktok_video(
    tiktok_url: str = Query(..., description="The URL of the TikTok video to download.")
):
    """
    API endpoint to download a TikTok video.
    Access this via: YOUR_VERCEL_URL/api/download?tiktok_url=...
    """
    
    # Placeholder: In a real app, complex logic resolves tiktok_url to direct_video_url.
    # For now, we use the input URL as the target for streaming.
    direct_video_url = tiktok_url 
    
    # Create a unique filename for the download
    file_name = f"tiktok_video_{os.urandom(4).hex()}.mp4"

    # Define the headers to force a download and set the media type
    headers = {
        "Content-Disposition": f"attachment; filename=\"{file_name}\"",
        "Content-Type": "video/mp4",
    }

    # Stream the content to the client
    return StreamingResponse(
        content=get_video_stream(direct_video_url),
        status_code=200,
        headers=headers,
        media_type="video/mp4" 
    )

# The 'app' variable is automatically detected by Vercel as the handler
# No need for an explicit 'handler = app' line if it's named 'app'.
