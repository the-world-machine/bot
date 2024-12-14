import os
from typing import List, Union
import music.youtube_manager as ytdl
from interactions.api.voice.audio import AudioVolume

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
    isrc: str = ''
    thumbnail: str = ''
    title: str = ''
    author: str = ''
    requester: User = None
    duration: int = 0
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
    
    tracks = await process_yt_track(url, True, ctx.author)
    queue.append(tracks)
    return [tracks]

async def play_track(module: Extension, ctx: Union[SlashContext, ComponentContext], track_id: int = 0):
    
    q = get_queue(ctx)
    
    if len(q) == 0:
        return 'empty_queue'
    
    target_track = q[track_id]
    
    del global_queue[ctx.guild_id][track_id]
    
    directory = f'bot/music/output/{str(ctx.guild_id)}'
    file_directory = os.path.join(directory + '/output')
    
    if not ctx.voice_state:
        raise ValueError("Not in voice channel to play audio")
        
    # Get the audio using YTDL
    audio = AudioVolume(file_directory)
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
    i.isrc = d.isrc
    i.url = d.url
        
    return i

async def process_yt_playlist(url: str, requester: User):
    try:
        data = ytdl.get_playlist_info(url)['entries']
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
        
        i.set_duration(d['duration'])
        
        tracks.append(i)
    
    return tracks
    
async def process_yt_track(url: str, download: bool, requester: User):
    i = Track()
    
    try:
        if 'ytsearch:' in url:
            d = ytdl.get_track_info(url, download)['data']['entries'][0]
            url = d['url']
        else:
            d = ytdl.get_track_info(url, download)['data']
    except Exception as e:
        print(e)
        i.error = TrackError.PROCESSING
        return i
    
    i.title = d['title']
    i.url = url
    i.author = d['uploader']
    i.thumbnail = d['thumbnails'][-1]['url']
    i.requester = requester
    
    i.set_duration(d['duration'])
    
    return i