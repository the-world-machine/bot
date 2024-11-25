import asyncio
import json
import yt_dlp

def get_playlist_info(url: str):
    with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist'}) as ydl:
        return ydl.extract_info(url, download=False) 

def get_track_info(url: str):
    with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        
        return {'data': info, 'type': 'track'}
    
async def quick_search(search: str):
    
    loop = asyncio.get_event_loop()
    
    with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'skip_download': True, 'noplaylist': True}) as ydl:
        info = await loop.run_in_executor(None, ydl.extract_info, search, False)
        
        return {'data': info, 'type': 'track'}