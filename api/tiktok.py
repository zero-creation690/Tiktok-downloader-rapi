import requests
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Iterator

# Initialize the FastAPI application
app = FastAPI()

# --- Utility Functions ---

def get_video_stream(url: str) -> Iterator[bytes]:
    """
    Handles fetching and streaming the video content chunk by chunk.
    """
    try:
        # We use the provided URL here as the target for streaming.
        # Set stream=True for chunked downloading.
        response = requests.get(url, stream=True, timeout=30) 
        
        if response.status_code != 200:
            print(f"Failed to fetch content from {url}. Status: {response.status_code}")
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


@app.get("/tiktok") # <-- CHANGED: The internal route now explicitly matches '/tiktok'
async def download_tiktok_video(
    tiktok_url: str = Query(..., description="The URL of the TikTok video to download.")
):
    """
    API endpoint to download a TikTok video.
    Access this via: YOUR_VERCEL_URL/api/tiktok?tiktok_url=...
    """
    
    # Placeholder: Assuming the input URL is ready for streaming
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
