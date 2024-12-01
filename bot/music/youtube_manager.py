import asyncio
import json
import os
import yt_dlp

def get_playlist_info(url: str):
    with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist'}) as ydl:
        return ydl.extract_info(url, download=False) 

def get_track_info(url: str, download: bool = False):
    
    directory = f'bot/music/output/1017479547664482444'
    dir_ = os.path.join(directory + '/output')
    
    opt = {
        'noplaylist': True,
        'format': 'm4a/bestaudio/best',
        'outtmpl': dir_,
    # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }]
    }
    
    with yt_dlp.YoutubeDL(opt) as ydl:
        info = ydl.extract_info(url, download=False)
        
        return {'data': info, 'type': 'track'}
    
async def quick_search(search: str):
    
    loop = asyncio.get_event_loop()
    
    with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'skip_download': True, 'noplaylist': True}) as ydl:
        info = await loop.run_in_executor(None, ydl.extract_info, search, False)
        
        return {'data': info, 'type': 'track'}
    
def download(url: str, dir: str):
    
    opt = {
        'noplaylist': True,
        'format': 'm4a/bestaudio/best',
        'outtmpl': dir,
    # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }]
    }
    
    with yt_dlp.YoutubeDL(opt) as ydl:
        ydl.download(url)