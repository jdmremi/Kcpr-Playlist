import spotipy
import sys
import logging
import coloredlogs
from spotipy.oauth2 import SpotifyOAuth
from difflib import SequenceMatcher

# Log initializers
stdout_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler('logs.log')
coloredlogs.install(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(stdout_handler)
logger.addHandler(file_handler)


class SpotifyAuthManager:
    """
    SpotifyAuthManager is a class that manages authentication and interactions with the Spotify API.
    Methods:
        __init__(client_id: str, client_secret: str, redirect_uri: str, scopes: str, user_id: str):
        create_playlist(title: str, description: str) -> str:
        add_tracks_to_playlist(playlist_id: str, tracks: list) -> None:
        get_tracks_from_album(artist_name: str, title: str, similarity_threshold: float = 0.95) -> list:
        get_track(artist_name: str, title: str, similarity_threshold: float = 0.95) -> str:
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: str, user_id: str):
        """
        Initializes the Spotify client with the provided credentials and settings.

        Args:
            client_id (str): The client ID for the Spotify application.
            client_secret (str): The client secret for the Spotify application.
            redirect_uri (str): The redirect URI for the Spotify application.
            scopes (str): A space-separated list of scopes for the Spotify application.
            user_id (str): The user ID for the Spotify user.

        Attributes:
            spotify (spotipy.Spotify): An instance of the Spotipy Spotify client authenticated with the provided credentials.
        """
        self.spotify: spotipy.Spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scopes,
            )
        )

        self.__client_id: str = client_id
        self.__client_secret: str = client_secret
        self.__redirect_uri: str = redirect_uri
        self.__scopes: str = scopes
        self.__user_id: str = user_id

    def create_playlist(self, title: str, description: str = "Curated by yours truly.") -> str:
        """
        Creates a new playlist on Spotify with the given title and description.

        Args:
            title (str): The title of the playlist.
            description (str): The description of the playlist.

        Returns:
            str: The ID of the created playlist.
        """
        created_playlist: any = self.spotify.user_playlist_create(
            user=self.__user_id, name=title, description=description)
        return created_playlist["id"]

    def add_tracks_to_playlist(self, playlist_id: str, tracks: list) -> None:
        """
        Adds a list of tracks to a specified Spotify playlist.

        Args:
            playlist_id (str): The Spotify ID of the playlist to which tracks will be added.
            tracks (list): A list of track URIs to be added to the playlist.

        Returns:
            None: Returns None.
        """

        # If trying to add a track with ID of '' to playlist and there's only one track provided, work around it.
        # Todo: Debug why this ID is sometimes blank.
        if '' in tracks and len(tracks) == 1:
            logger.warning(f"Empty track ID found.")

        # Here's a lazy workaround for the issue mentioned above.
        try:
            logger.debug(f"Track IDs to be added = {tracks}")
            # If more than 99 tracks, we need to split it into chunks.
            if len(tracks) >= 99:
                chunks: list[list] = Utils.divide_chunks(tracks)
                for chunk in chunks:
                    self.spotify.playlist_add_items(playlist_id, chunk)
            else:
                self.spotify.playlist_add_items(playlist_id, tracks)

        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")

    def add_track_to_playlist(self, playlist_id: str, track_id: str) -> None:
        """
        Adds a single track to a specified Spotify playlist.

        Args:
            playlist_id (str): The Spotify ID of the playlist to which tracks will be added.
            track_id (str): The track ID to be added to the playlist.

        Returns:
            None
        """

        self.add_tracks_to_playlist(playlist_id=playlist_id, tracks=[track_id])

    def get_tracks_from_album(self, artist_name: str, title: str, similarity_threshold: float = 0.95) -> list:
        """
        Retrieves the track URIs from an album on Spotify based on the artist name and album title.

        Args:
            artist_name (str): The name of the artist.
            title (str): The title of the album.
            similarity_threshold (float, optional): The threshold for string similarity to match the artist name and album title. Defaults to 0.95.

        Returns:
            list: A list of track URIs from the album if found, otherwise an empty list.
        """
        query: str = f"{artist_name} {title}"
        album_query: dict = self.spotify.search(query, type="album")
        albums: list = album_query["albums"]["items"]

        if not albums:
            return []

        album: dict = albums[0]
        album_id: str = album["uri"]

        if similarity_threshold == 0.0:
            album_tracks_query: dict = self.spotify.album_tracks(
                album_id=album_id)
            return [track["uri"] for track in album_tracks_query["items"]]

        album_name: str = album["name"]
        artist: str = album["artists"][0]["name"]
        artist_similarity: float = Utils.str_similarity(artist, artist_name)
        title_similarity: float = Utils.str_similarity(title, album_name)

        if artist_similarity >= similarity_threshold and title_similarity >= similarity_threshold:
            as_percentage: float = artist_similarity * 100.0
            ts_percentage: float = title_similarity * 100.0
            print(f"Artist similarity: {
                  as_percentage:.2f}% | Title similarity: {ts_percentage:.2f}%")
            album_tracks_query: dict = self.spotify.album_tracks(
                album_id=album_id)
            return [track["uri"] for track in album_tracks_query["items"]]

        return []

    def get_track(self, artist_name: str, title: str, similarity_threshold: float = 0.95) -> str:
        """
        Searches for a track on Spotify based on the provided artist name and title.

        Args:
            artist_name (str): The name of the artist.
            title (str): The title of the track.
            similarity_threshold (float, optional): Threshold for string similarity to consider a match. Defaults to 0.95.

        Returns:
            str: The URI of the track if found and matches the similarity threshold, otherwise an empty string.
        """
        # Combine artist name and title for the query.
        query: str = f"{artist_name} {title}"
        track_query: dict = self.spotify.search(query, type="track", limit=5)
        tracks: list = track_query["tracks"]["items"]

        track: dict = tracks[0]
        if similarity_threshold == 0.0:
            return track["uri"]

        # Check similarity of artist and track names.
        artist: str = track["artists"][0]["name"]
        track_name: str = track["name"]
        artist_similarity: float = Utils.str_similarity(artist, artist_name)
        title_similarity: float = Utils.str_similarity(track_name, title)

        if artist_similarity >= similarity_threshold and title_similarity >= similarity_threshold:
            as_percentage: float = artist_similarity * 100.0
            ts_percentage: float = title_similarity * 100.0
            print(f"Artist similarity: {
                  as_percentage:.2f}% | Title similarity: {ts_percentage:.2f}%")
            return track["uri"]

        return ""

    def get_playlist_tracks(self, playlist_id: str) -> list[str]:
        """
        This Python function retrieves all tracks from a playlist using the Spotify API.

        Returns:
            str: A list of track URIs
        """
        playlist_query: dict = self.spotify.playlist_items(
            playlist_id=playlist_id, limit=100)
        tracks: list[dict] = playlist_query["items"]
        while playlist_query["next"]:
            playlist_query: dict = self.spotify.next(playlist_query)
            tracks.extend(playlist_query["items"])

        track_uris: list[str] = [track["track"]["id"] for track in tracks]
        return track_uris


class Utils:
    """
        A utility class providing static methods, such as string similarity comparison and list chunking.

        Methods:
            str_similarity(lhs_title: str, rhs_title: str) -> float:
    """
    @staticmethod
    def str_similarity(lhs_title: str, rhs_title: str) -> float:
        """
        Calculate the similarity ratio between two strings using the SequenceMatcher.

        Args:
            lhs_title (str): The first string to compare.
            rhs_title (str): The second string to compare.

        Returns:
            float: A float value between 0 and 1 representing the similarity ratio
                   between the two input strings. A value of 1 indicates identical
                   strings, while 0 indicates completely different strings.
        """
        return SequenceMatcher(None, lhs_title, rhs_title).ratio()
