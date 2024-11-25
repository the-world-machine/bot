import music.youtube_manager as ytdl

from utilities.config import get_config
from music.spotify_api import Spotify, SpotifyTrack

spotify = Spotify(get_config('music.spotify.id'), get_config('music.spotify.secret'))

from enum import Enum
from dataclasses import dataclass
from interactions import User

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
    error: TrackError = TrackError.NONE
        
    def set_duration(self, seconds: float):
        self.duration = seconds * 1000

async def add_search(url: str, requester: User):
    
    if 'open.spotify.com' in url:
        if 'playlist' in url or 'album' in url:
            return await process_spotify_playlist(url, requester)
    
    if '/sets/' in url:
        return Track(error=TrackError.SOUNDCLOUD_PLAYLIST)
    
    if url[0:8] != 'https://':
        url = 'ytsearch:' + url
        return [await process_yt_track(url, requester)]
    
    if 'youtube.com/playlist' in url:
        return await process_yt_playlist(url, requester)
    
    return [await process_yt_track(url, requester)]

async def process_spotify_playlist(url: str, requester: User):
    data = await spotify.get_playlist(url)
    
    for d in data:
        d: SpotifyTrack
        
        i = await ytdl.quick_search(f'ytsearch:{d.isrc}')
    
    pass

async def process_spotify_track(url: str, requester: User):
    pass

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
    
async def process_yt_track(url: str, requester: User):
    i = Track()
    
    try:
        if 'ytsearch:' in url:
            d = ytdl.get_track_info(url)['data']['entries'][0]
            url = d['url']
        else:
            d = ytdl.get_track_info(url)['data']
    except:
        i.error = TrackError.PROCESSING
        return i
    
    i.title = d['title']
    i.url = url
    i.author = d['uploader']
    i.thumbnail = d['thumbnails'][-1]['url']
    i.requester = requester
    
    i.set_duration(d['duration'])
    
    return i

async def init():    
    await add_search('https://www.youtube.com/playlist?list=PL_JhyGGuvnSTVg5T9JNLWenLYKPO4A8hS', None)