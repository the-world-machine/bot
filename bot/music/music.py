import os
from typing import List, Union
import music.music_api as music_api
from interactions.api.voice.audio import AudioVolume, RawInputAudio
import asyncio
from utilities.config import get_config
from music.spotify_api import Spotify, SpotifyTrack

spotify = Spotify(get_config('music.spotify.id'), get_config('music.spotify.secret'))

from enum import Enum
from dataclasses import dataclass
from interactions import ComponentContext, Extension, SlashContext, User

class TrackError(Enum):
    NONE = -1
    SOUNDCLOUD_PLAYLIST = 0
    PROCESSING = 1

@dataclass
class Track:
    url: str = ''
    thumbnail: str = ''
    title: str = ''
    author: str = ''
    requester: User = None
    duration: int = 0
    query: str = ''
    error: TrackError = TrackError.NONE
        
    def set_duration(self, seconds: float):
        self.duration = seconds * 1000
        
global_queue = {}

def get_queue(ctx:Union[SlashContext, ComponentContext]) -> List[Track]:
    if ctx.guild_id not in global_queue:
        global_queue[ctx.guild_id] = []
        
    return global_queue[ctx.guild_id]

async def add_search(url: str, ctx: Union[SlashContext, ComponentContext]):
        
    queue = get_queue(ctx)
    
    if 'open.spotify.com' in url:
        if 'playlist' in url or 'album' in url:
            tracks = await process_spotify_playlist(url, ctx.author)
            queue += tracks
            return tracks
        
        tracks = await process_spotify_track(url, ctx.author)
        queue.append(tracks)
        return [tracks]
    
    if '/sets/' in url:
        return [Track(error=TrackError.SOUNDCLOUD_PLAYLIST)]
    
    if url[0:8] != 'https://':
        url = 'ytsearch:' + url
        tracks = await process_yt_track(url, ctx.author)
        queue.append(tracks)
        return [tracks]
    
    if 'youtube.com/playlist' in url:
        tracks = await process_yt_playlist(url, ctx.author)
        queue += tracks
        return tracks
    
    tracks = await process_yt_track(url, ctx.author)
    queue.append(tracks)
    return [tracks]

async def play_track(ctx: Union[SlashContext, ComponentContext], track_id: int = 0):
    
    q = get_queue(ctx)
    
    target_track = q[track_id]
    
    track_api_id = await music_api.get_track(str(ctx.author.id), target_track.query)
    
    if track_api_id is None:
        return 'api_error'
    
    if len(q) == 0:
        return 'empty_queue'
    
    del global_queue[ctx.guild_id][track_id]
    
    if not ctx.voice_state:
        raise ValueError("Not in voice channel to play audio")
    
    audio_data: bytearray = await music_api.download_track(str(ctx.author.id), track_api_id)
    
    audio = RawInputAudio(None, audio_data)
    
    await ctx.send(f"Now Playing: **{target_track.title}**\n{target_track.thumbnail}")
    # Play the audio
    await ctx.voice_state.play(audio)

async def process_spotify_playlist(url: str, requester: User):
    data: list[SpotifyTrack] = await spotify.get_playlist(url)
    
    tracks = []
    
    for d in data:
        
        if d is None:
            continue
        
        i = Track()
        i.title = d.name
        i.thumbnail = d.album['images'][0]['url']
        i.author = d.artist
        i.requester = requester
        i.duration = d.duration
        i.isrc = d.isrc
        i.url = d.url
        
        tracks.append(i)
        
    return tracks

async def process_spotify_track(url: str, requester: User):
    d: SpotifyTrack = await spotify.get_track(url)

    if d is None:
        return Track(error=TrackError.PROCESSING)
    
    i = Track()
    i.title = d.name
    i.thumbnail = d.album['images'][0]['url']
    i.author = d.artist
    i.requester = requester
    i.duration = d.duration
    i.url = d.url
    i.query = f'ytsearch:{d.isrc}'
        
    return i

async def process_yt_playlist(url: str, requester: User):
    try:
        data = await music_api.get_playlist_info(url)['entries']
    except:
        i.error = TrackError.PROCESSING
        return i
    
    tracks = []
    
    for d in data:
        if d.get('uploader', None) == None: # This usually means the track is privated or deleted.
            continue
        
        i = Track()

        i.title = d['title']
        i.url = d['url']
        i.author = d['uploader']
        i.thumbnail = d['thumbnails'][-1]['url']
        i.requester = requester
        i.query = d['url']
        
        i.set_duration(d['duration'])
        
        tracks.append(i)
    
    return tracks
    
async def process_yt_track(url: str, requester: User):
    i = Track()
    
    try:
        
        track_info = await music_api.get_track_info(url)
        
        if 'ytsearch:' in url:
            d = track_info['data']['entries'][0]
            url = d['url']
        else:
            d = track_info['data']
    except Exception as e:
        print(e)
        i.error = TrackError.PROCESSING
        return i
    
    i.title = d['title']
    i.url = url
    i.author = d['uploader']
    i.thumbnail = d['thumbnails'][-1]['url']
    i.requester = requester
    i.query = url
    
    i.set_duration(d['duration'])
    
    return i