from typing import Dict
import aiohttp
from dataclasses import dataclass

@dataclass
class SpotifyTrack:
    
    name: str
    artist: str
    album: dict
    url: str
    duration: int
    id: str
    isrc: str

def create_track(data: dict):
    
    try:
        return SpotifyTrack(**{
            "artist": data["artists"][0]["name"],
            "url": data['external_urls']['spotify'],
            "isrc": data['external_ids']['isrc'],
            "duration": data['duration_ms'],
            "name": data["name"],
            "album": data["album"],
            "id": data["id"],
        })
    except:
        pass

class Spotify:
    def __init__(self, client_id, secret):
        self.client_id = client_id
        self.secret = secret

    async def get_access_token(self):
        auth_url = "https://accounts.spotify.com/api/token"

        # Your client_id and secret
        client_id = self.client_id
        secret = self.secret

        # Define the headers for the token request
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        # Define the data for the token request
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as resp:
                response_data = await resp.json()
                # The access token is in response_data['access_token']
                return response_data['access_token']

    async def get_track(self, query):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        if 'open.spotify.com/track/' in query:

            query = query.replace('https://open.spotify.com/track/', '')
            query = query.replace('http://open.spotify.com/track/', '')

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/tracks/{query}/", headers=headers) as resp:
                    data = await resp.json()
                    return create_track(data)
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1",
                                       headers=headers) as resp:
                    data = await resp.json()
                    track = data['tracks']['items'][0]
                    return create_track(track)

    async def get_playlist(self, url):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        if 'open.spotify.com/playlist/' in url:
            url = url.replace('https://open.spotify.com/playlist/', '')
            url = url.replace('http://open.spotify.com/playlist/', '')
            async with aiohttp.ClientSession() as session:

                url = f"https://api.spotify.com/v1/playlists/{url}"
                tracks = []

                while True:

                    async with session.get(url, headers=headers) as resp:

                        try:
                            data = await resp.json()
                        except:
                            return None

                        try:
                            get_items = data['tracks']
                        except:
                            get_items = data

                        for item in get_items['items']:
                            track = create_track(item['track'])

                            tracks.append(track)

                        url = get_items['next']

                        if url is None:
                            break

                return tracks
        else:
            async with aiohttp.ClientSession() as session:
                url = url.replace('https://open.spotify.com/album/', '')
                url = url.replace('http://open.spotify.com/album/', '')
                async with session.get(f"https://api.spotify.com/v1/albums/{url}", headers=headers) as resp:
                    data = await resp.json()

                    tracks = []

                    for item in data['tracks']['items']:
                        
                        track = await self.get_track(f'https://open.spotify.com/track/{item["id"]}')

                        tracks.append(track)

                    return tracks

    async def search(self, query, limit=25, type='track'):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.spotify.com/v1/search?q={query}&type={type}&limit={limit}",
                                   headers=headers) as resp:

                try:
                    data = await resp.json()
                except:
                    return 'error'

                return data
