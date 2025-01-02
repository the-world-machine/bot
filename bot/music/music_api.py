import asyncio
from time import sleep
import aiohttp
import json
import os
import yt_dlp
import urllib.parse
from interactions.api.voice.audio import AudioBuffer, BaseAudio, RawInputAudio

base_url = 'http://127.0.0.1:5000/'
api_key = 'test_api_key'

async def get_track(uid: str, url: str):
    safe_url = urllib.parse.quote_plus(url)
    
    request_url = base_url + f'/get?uid={uid}&query={safe_url}&api_key={api_key}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(request_url) as resp:
            response_data = await resp.json()
            
            return response_data['tid']
    return None

async def download_track(uid: str, tid: int):
    request_url = base_url + f'/download?uid={uid}&tid={tid}&api_key={api_key}'
    
    save_path = os.path.join('output')
    _bytes = bytearray()
       
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(request_url) as resp:
                if resp.status == 202:
                    # The download is still in progress, wait and retry
                    await asyncio.sleep(1)  # Wait for a second before retrying
                    continue
                elif resp.status == 200:
                    
                    while True:
                        chunk = await resp.content.read(1024)  # Read in chunks
                        if not chunk:
                            break
                        _bytes.extend(chunk)
                    
                    print(f"File downloaded successfully and saved to {save_path}")
                    return _bytes
                else:
                    print(f"Error: {resp.status}")
                    break
                
async def get_playlist_info(url: str):
    safe_url = urllib.parse.quote_plus(url)
    
    request_url = base_url + f'/playlist_info?url={safe_url}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(request_url) as resp:
            return await resp.json()

async def get_track_info(url: str):
    safe_url = urllib.parse.quote_plus(url)
    
    request_url = base_url + f'/track_info?url={safe_url}'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(request_url) as resp:
            return await resp.json()