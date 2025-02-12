import schedule
import time
import logging
import coloredlogs
import os
import sys
from kcpr import KcprHandler
from spotify import SpotifyAuthManager
from dotenv import load_dotenv
from datetime import datetime

# Load .env vars
load_dotenv()

# Spotify OAuth manager stuff
CLIENT_ID: str = os.getenv("CLIENT_ID")
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET")
REDIRECT_URI: str = os.getenv("REDIRECT_URI")
SCOPES: str = os.getenv("SCOPES")
USER_ID: str = os.getenv("USER_ID")
PLAYLIST_ID: str = os.getenv("PLAYLIST_ID")

# Log initializers
stdout_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler('logs.log')
coloredlogs.install(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(stdout_handler)
logger.addHandler(file_handler)


class KcprSpotifyScheduler():
    """
    A scheduler class that integrates KCPR's currently playing song with a Spotify playlist.

    Attributes:
        kcpr_handler (KcprHandler): Handler for KCPR's now playing data.
        spotify_handler (SpotifyAuthManager): Manager for Spotify authentication and API interactions.
        spotify_playlist_track_uris (list[str]): List of track URIs in the Spotify playlist to avoid duplicates.
        prev_data (str): The previously playing song data to detect changes.

    Methods:
        __init__():
            Initializes the KcprSpotifyScheduler with KCPR and Spotify handlers and retrieves the initial playlist tracks.

        __spotify_kcpr_event():
            Checks for changes in the currently playing song on KCPR, searches for the song on Spotify, and adds it to the playlist if it's not already present.

        schedule():
            Starts the scheduler to check for new songs every minute.
    """

    def __init__(self):
        """
        Initializes the Scheduler class.

        This constructor sets up the necessary handlers for KCPR and Spotify, and initializes
        the list of track URIs in the Spotify playlist to avoid duplicates. It also retrieves
        the currently playing song from KCPR.

        Attributes:
            kcpr_handler (KcprHandler): Handler for KCPR operations.
            spotify_handler (SpotifyAuthManager): Manager for Spotify authentication and operations.
            spotify_playlist_track_uris (list[str]): List of track URIs in the Spotify playlist.
            prev_data (str): The currently playing song data from KCPR.
        """
        self.kcpr_handler: KcprHandler = KcprHandler()
        self.spotify_handler: SpotifyAuthManager = SpotifyAuthManager(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scopes=SCOPES, user_id=USER_ID)
        # Used to keep track of the tracks in the playlist to avoid duplicates.
        self.spotify_playlist_track_uris: list[str] = self.spotify_handler.get_playlist_tracks(playlist_id=PLAYLIST_ID
                                                                                               )
        
        # Get the currently playing song
        artist, song = self.kcpr_handler.get_now_playing()
        
        # Format query
        query: str = f"{artist} - {song}"

        # Get the currently playing song
        self.prev_data: str = query

    def __spotify_kcpr_event(self) -> None:
        """
        Handles the event of fetching the currently playing song from KCPR and updating the Spotify playlist.

        This method performs the following steps:
        1. Retrieves the currently playing song from the KCPR handler.
        2. Formats the song information into a query string.
        3. Checks if this is the first request after restarting and initializes the previous data if so.
        4. Compares the current song with the previously fetched song.
        5. If the song has changed, it fetches the track URI from Spotify.
        6. Adds the track to the Spotify playlist if it is not already present.
        7. Logs the addition of the track to the playlist.
        8. Updates the previous data to the current song.

        Logging:
        - Logs the currently playing song.
        - Logs the addition of new tracks to the playlist.
        - Logs if the track is already in the playlist.
        - Logs if there is no new data.

        Returns:
            None
        """
        # Get the currently playing song
        artist, song = self.kcpr_handler.get_now_playing()

        # Convert the format to a string of the format "artist - song"
        query: str = f"{artist} - {song}"

        # If first request after restarting, do nothing.
        if self.prev_data is None:
            self.prev_data = query
        # If we have new data
        if self.prev_data != query:
            logger.debug(f"Now playing: {query}")
            # Get the track from Spotify
            track_uri: str = self.spotify_handler.get_track(
                artist_name=artist, title=song, similarity_threshold=0.30)

            # If the track is not in our playlist, then we'll add it.
            if not track_uri in self.spotify_playlist_track_uris:
                self.spotify_handler.add_track_to_playlist(
                    playlist_id=PLAYLIST_ID, track_id=track_uri)
                self.spotify_playlist_track_uris.append(track_uri)
                logger.debug(f"Added track to playlist: {query}")

                # Log the event in the format: DD MM YYYY HH:MM:SS - [query](link to spotify track)
                # Get track ID since Spotify URIs are in the format spotify:track:track_id
                track_id: str = track_uri.split(":")[-1]
                # Log to file
                logger.info(
                    f"{datetime.now()} {query} (https://open.spotify.com/track/{track_id})")

                # Update the previous data to be currently playing song.
                self.prev_data = query

                # Add the track ID to the playlist track IDs to avoid duplicates.
                self.spotify_playlist_track_uris.append(track_uri)

            else:
                logger.debug(f"Track already in playlist: {query}")
        else:
            logger.debug("No new data...")

    def schedule(self):
        logger.debug("Scheduler started.")
        schedule.every().minute.do(self.__spotify_kcpr_event)


if __name__ == "__main__":
    kcpr_scheduler: KcprSpotifyScheduler = KcprSpotifyScheduler()
    kcpr_scheduler.schedule()

    while True:
        # Run the scheduler
        schedule.run_pending()
        # Usually adding a sleep(1) or even sleep(0.001) in a small infinite loop is done to prevent python from using 100% of a core of your CPU.
        # See: https://stackoverflow.com/questions/373335/how-do-i-get-a-cron-like-scheduler-in-python
        time.sleep(1)
