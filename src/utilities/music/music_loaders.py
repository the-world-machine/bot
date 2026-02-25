from lavalink import DeferredAudioTrack, LoadResult, LoadType, PlaylistInfo, Source

from utilities.config import get_config
from utilities.music.spotify_api import Spotify

spotify_creds: dict = get_config("music.spotify", typecheck=dict)
spotify = Spotify(client_id=spotify_creds["id"], secret=spotify_creds["secret"])


class CustomAudioTrack(DeferredAudioTrack):
	# A DeferredAudioTrack allows us to load metadata now, and a playback URL later.
	# This makes the DeferredAudioTrack highly efficient, particularly in cases
	# where large playlists are loaded.

	async def load(self, client):  # Load our 'actual' playback track using the metadata from this one.
		isrc_search = f'ytmsearch:"{self.isrc}"'
		bc_search = f"bcsearch:{self.title} {self.author}"
		last_search = f"ytmsearch:{self.title} {self.author}"

		result: LoadResult = await client.get_tracks(isrc_search, check_local=True)

		if result.load_type == LoadType.EMPTY:
			result: LoadResult = await client.get_tracks(bc_search, check_local=True)

		if result.load_type == LoadType.EMPTY:
			result: LoadResult = await client.get_tracks(last_search, check_local=True)

		first_track = result.tracks[0]  # Grab the first track from the results.
		base64 = first_track.track  # Extract the base64 string from the track.
		self.track = base64  # We'll store this for later, as it allows us to save making network requests
		# if this track is re-used (e.g. repeat).

		return base64


class CustomSearch(Source):

	def __init__(self):
		super().__init__(name="custom")  # Initialising our custom source with the name 'custom'.

	async def load_item(self, client, query: str):
		if "open.spotify.com" in query:
			load_type = LoadType.TRACK

			if "playlist" in query or "album" in query:
				tracks = await spotify.get_playlist(query)

				load_type = LoadType.PLAYLIST
			else:
				tracks = [await spotify.get_track(query)]

			get_tracks = []

			if tracks is None:
				return LoadResult(load_type, get_tracks, playlist_info=PlaylistInfo.none())

			for t in tracks:
				if t is None:
					continue

				get_tracks.append(
					CustomAudioTrack(
						{  # Create an instance of our CustomAudioTrack.
							"identifier": t.album["images"][0][
								"url"
							],  # Fill it with metadata that we've obtained from our source's provider.
							"isSeekable": True,
							"author": t.artist,
							"title": t.name,
							"length": t.duration,
							"isStream": False,
							"uri": t.url,
							"isrc": t.isrc,
						},
						requester=0,
						extra={"album_name": t.album["name"]},
					)
				)  # Init requester with a default value.

			return LoadResult(load_type, get_tracks, playlist_info=PlaylistInfo.none())
